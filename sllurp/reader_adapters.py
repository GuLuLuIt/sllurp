"""Unified management adapters for RFID readers.

This module layers vendor-aware operations on top of :mod:`sllurp.reader_management`.
LLRP inventory remains independent from these administrative HTTP/HTTPS APIs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlencode

from .reader_management import (
    HTTPReaderManager,
    ReaderHTTPResponse,
    ReaderManagementError,
)


class ReaderManagementUnsupported(ReaderManagementError):
    """Raised when a reader family does not expose a requested operation."""


@dataclass(frozen=True)
class ReaderIdentity:
    """Normalized reader identity returned by management adapters."""

    vendor: str
    model: str | None = None
    serial_number: str | None = None
    firmware: str | None = None


class ReaderManager:
    """Base capability-oriented reader management interface."""

    vendor = "unknown"
    models: frozenset[str] = frozenset()
    capabilities: frozenset[str] = frozenset()

    def __init__(self, model: str | None = None) -> None:
        self.model = model

    def supports(self, operation: str) -> bool:
        """Return whether this adapter implements *operation*."""
        return operation in self.capabilities

    def require(self, operation: str) -> None:
        """Raise a normalized error when *operation* is unavailable."""
        if not self.supports(operation):
            model = f" {self.model}" if self.model else ""
            raise ReaderManagementUnsupported(
                f"{self.vendor}{model} does not expose {operation!r} through "
                "this management adapter"
            )

    def identity(self) -> ReaderIdentity:
        self.require("identity")
        raise AssertionError("adapter capability declared without implementation")

    def get_status(self) -> Any:
        self.require("status")
        raise AssertionError("adapter capability declared without implementation")

    def get_settings(self) -> Any:
        self.require("settings")
        raise AssertionError("adapter capability declared without implementation")

    def update_settings(self, settings: Mapping[str, Any]) -> Any:
        self.require("settings")
        raise AssertionError("adapter capability declared without implementation")

    def reboot(self) -> Any:
        self.require("reboot")
        raise AssertionError("adapter capability declared without implementation")


def _response_json(response: ReaderHTTPResponse) -> Any:
    if not response.body:
        return None
    return response.json()


class ZebraReaderManager(ReaderManager):
    """Zebra fixed-reader local REST management adapter.

    The ``/cloud`` API is documented for Zebra IoT Connector readers. FXR90
    firmware exposes a related fixed-reader management surface; callers should
    use :meth:`supports` rather than assuming every firmware exposes every route.
    """

    vendor = "zebra"
    models = frozenset({"FX7500", "FX9600", "ATR7000", "FXR90"})
    capabilities = frozenset(
        {
            "identity",
            "status",
            "settings",
            "network",
            "reboot",
            "mode",
            "inventory",
            "reader_capabilities",
            "regions",
            "gpi",
            "gpo",
            "led",
            "timezone",
            "ntp",
            "logs",
            "device_name",
            "apps",
            "certificates",
            "firmware",
            "raw",
        }
    )

    def __init__(
        self,
        base_url: str,
        *,
        model: str | None = None,
        username: str | None = None,
        password: str | None = None,
        bearer_token: str | None = None,
        timeout: float = 5.0,
        verify_tls: bool = True,
        ca_file: str | None = None,
        cert_file: str | None = None,
        key_file: str | None = None,
    ) -> None:
        super().__init__(model=model)
        self.base_url = base_url
        self._http_options = {
            "timeout": timeout,
            "verify_tls": verify_tls,
            "ca_file": ca_file,
            "cert_file": cert_file,
            "key_file": key_file,
        }
        self._credentials = (username, password)
        self._login_transport: HTTPReaderManager | None = None
        if username is not None or password is not None:
            if username is None or password is None:
                raise ValueError("username and password must be supplied together")
            self._login_transport = HTTPReaderManager(
                base_url, username=username, password=password, **self._http_options
            )

        self._transport = HTTPReaderManager(
            base_url, bearer_token=bearer_token, **self._http_options
        )
        self._needs_login = bearer_token is None and self._login_transport is not None

    @staticmethod
    def _extract_token(payload: Any, text: str) -> str | None:
        token = None
        if isinstance(payload, Mapping):
            for key in (
                "token",
                "bearerToken",
                "access_token",
                "accessToken",
                "jwt",
                "JWT",
                "message",
            ):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    token = value.strip()
                    break
        elif isinstance(payload, str):
            token = payload.strip()

        if not token:
            token = text.strip()
        for prefix in ("JWT Token:", "Bearer "):
            if token.startswith(prefix):
                token = token[len(prefix) :].strip()
        return token or None

    def login(self) -> str:
        """Exchange Zebra web-console credentials for a local REST bearer token."""
        if self._login_transport is None:
            raise ReaderManagementError(
                "Zebra login requires username/password; alternatively pass bearer_token"
            )
        response = self._login_transport.request("GET", "/cloud/localRestLogin")
        try:
            payload = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        token = self._extract_token(payload, response.text)
        if not token:
            raise ReaderManagementError(
                "Zebra localRestLogin succeeded but returned no bearer token",
                status=response.status,
                body=response.body,
            )
        self._transport = HTTPReaderManager(
            self.base_url, bearer_token=token, **self._http_options
        )
        self._needs_login = False
        return token

    def _manager(self) -> HTTPReaderManager:
        if self._needs_login:
            self.login()
        return self._transport

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        data: bytes | str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ReaderHTTPResponse:
        """Send an authenticated raw request to a Zebra management route."""
        return self._manager().request(
            method, path, json_body=json_body, data=data, headers=headers
        )

    def identity(self) -> ReaderIdentity:
        info = self.request("GET", "/cloud/version").json()
        model = info.get("model") if isinstance(info, Mapping) else self.model
        serial = info.get("serialNumber") if isinstance(info, Mapping) else None
        firmware = None
        if isinstance(info, Mapping):
            firmware = info.get("readerApplication") or info.get("radioFirmware")
        return ReaderIdentity(self.vendor, model or self.model, serial, firmware)

    def get_status(self) -> Any:
        return self.request("GET", "/cloud/status").json()

    def get_settings(self) -> Any:
        return self.request("GET", "/cloud/config").json()

    def update_settings(self, settings: Mapping[str, Any]) -> Any:
        return _response_json(
            self.request("PUT", "/cloud/config", json_body=dict(settings))
        )

    def get_network(self, interface: str | None = None) -> Any:
        body = {"interface": interface} if interface is not None else None
        return self.request("GET", "/cloud/network", json_body=body).json()

    def update_network(self, settings: Mapping[str, Any]) -> Any:
        return _response_json(
            self.request("PUT", "/cloud/network", json_body=dict(settings))
        )

    def reboot(self) -> Any:
        return _response_json(self.request("PUT", "/cloud/reboot"))

    def get_mode(self, *, verbose: bool | None = None) -> Any:
        body = None if verbose is None else {"verbose": bool(verbose)}
        return self.request("GET", "/cloud/mode", json_body=body).json()

    def set_mode(self, settings: Mapping[str, Any]) -> Any:
        return _response_json(
            self.request("PUT", "/cloud/mode", json_body=dict(settings))
        )

    def start_inventory(self, *, do_not_persist_state: bool | None = None) -> Any:
        body = None
        if do_not_persist_state is not None:
            body = {"doNotPersistState": bool(do_not_persist_state)}
        return _response_json(self.request("PUT", "/cloud/start", json_body=body))

    def stop_inventory(self) -> Any:
        return _response_json(self.request("PUT", "/cloud/stop"))

    def get_reader_capabilities(self) -> Any:
        return self.request("GET", "/cloud/readerCapabilities").json()

    def get_supported_regions(self) -> Any:
        return self.request("GET", "/cloud/supportedRegionList").json()

    def get_region(self) -> Any:
        return self.request("GET", "/cloud/region").json()

    def get_supported_standards(self, region: str) -> Any:
        if not region:
            raise ValueError("region must not be empty")
        return self.request(
            "GET", "/cloud/supportedStandardList", json_body={"region": region}
        ).json()

    def get_gpi(self) -> Any:
        return self.request("GET", "/cloud/gpi").json()

    def get_gpo(self) -> Any:
        return self.request("GET", "/cloud/gpo").json()

    def set_gpo(self, port: int, state: bool) -> Any:
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 4:
            raise ValueError("port must be an integer from 1 through 4")
        return _response_json(
            self.request(
                "PUT", "/cloud/gpo", json_body={"port": port, "state": bool(state)}
            )
        )

    def get_app_led(self) -> Any:
        return self.request("GET", "/cloud/app-led").json()

    def set_app_led(
        self, color: str, seconds: int, *, flash: bool = False
    ) -> Any:
        color = color.lower()
        if color not in {"red", "amber", "green", "off"}:
            raise ValueError("color must be red, amber, green, or off")
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
            raise ValueError("seconds must be a non-negative integer")
        query = urlencode(
            {"color": color, "seconds": seconds, "flash": str(bool(flash)).lower()}
        )
        return _response_json(self.request("PUT", f"/cloud/app-led?{query}"))

    def get_timezone(self) -> Any:
        return self.request("GET", "/cloud/timeZone").json()

    def set_timezone(self, settings: Mapping[str, Any]) -> Any:
        return _response_json(
            self.request("PUT", "/cloud/timeZone", json_body=dict(settings))
        )

    def get_ntp_server(self) -> Any:
        return self.request("GET", "/cloud/ntpServer").json()

    def set_ntp_server(self, settings: Mapping[str, Any]) -> Any:
        return _response_json(
            self.request("PUT", "/cloud/ntpServer", json_body=dict(settings))
        )

    def get_logs(self) -> Any:
        return self.request("GET", "/cloud/logs").json()

    def set_logs(self, settings: Mapping[str, Any]) -> Any:
        return _response_json(
            self.request("PUT", "/cloud/logs", json_body=dict(settings))
        )

    @staticmethod
    def _route_segment(value: str, name: str) -> str:
        if not value or "/" in value or value in {".", ".."}:
            raise ValueError(f"{name} must be a non-empty route segment")
        return value

    def get_log(self, log_type: str) -> ReaderHTTPResponse:
        log_type = self._route_segment(log_type, "log_type")
        return self.request("GET", f"/cloud/logs/{log_type}")

    def clear_log(self, log_type: str) -> Any:
        log_type = self._route_segment(log_type, "log_type")
        return _response_json(self.request("DELETE", f"/cloud/logs/{log_type}"))

    def get_name_and_description(self) -> Any:
        return self.request("GET", "/cloud/nameAndDescription").json()

    def set_name_and_description(self, name: str, description: str) -> Any:
        if not name:
            raise ValueError("name must not be empty")
        return _response_json(
            self.request(
                "PUT",
                "/cloud/nameAndDescription",
                json_body={"name": name, "description": description},
            )
        )

    def list_apps(self) -> Any:
        return self.request("GET", "/cloud/apps").json()

    def install_app(self, settings: Mapping[str, Any]) -> Any:
        return _response_json(
            self.request("PUT", "/cloud/apps/install", json_body=dict(settings))
        )

    def _app_action(
        self, appname: str, action: str, payload: Mapping[str, Any] | None = None
    ) -> Any:
        appname = self._route_segment(appname, "appname")
        return _response_json(
            self.request(
                "PUT",
                f"/cloud/apps/{appname}/{action}",
                json_body=dict(payload) if payload is not None else None,
            )
        )

    def uninstall_app(self, appname: str) -> Any:
        return self._app_action(appname, "uninstall")

    def start_app(self, appname: str) -> Any:
        return self._app_action(appname, "start")

    def stop_app(self, appname: str) -> Any:
        return self._app_action(appname, "stop")

    def set_app_autostart(self, appname: str, enabled: bool) -> Any:
        return self._app_action(appname, "autostart", {"autostart": bool(enabled)})

    def app_request(
        self, appname: str, command: str, *, userapp: str | None = None
    ) -> Any:
        payload = {"userapp": userapp or appname, "command": command}
        return self._app_action(appname, "pass-through", payload)

    def list_certificates(self) -> Any:
        return self.request("GET", "/cloud/certificates").json()

    def install_certificate(
        self, certname: str, settings: Mapping[str, Any]
    ) -> Any:
        certname = self._route_segment(certname, "certname")
        return _response_json(
            self.request(
                "PUT",
                f"/cloud/certificates/{certname}",
                json_body=dict(settings),
            )
        )

    def refresh_certificate(self, certname: str, cert_type: str) -> Any:
        certname = self._route_segment(certname, "certname")
        if cert_type not in {"server", "client", "app"}:
            raise ValueError("cert_type must be server, client, or app")
        return _response_json(
            self.request(
                "PUT",
                f"/cloud/certificates/{certname}",
                json_body={"type": cert_type},
            )
        )

    def delete_certificate(self, certname: str, cert_type: str) -> Any:
        certname = self._route_segment(certname, "certname")
        if cert_type not in {"client", "app"}:
            raise ValueError("cert_type must be client or app")
        return _response_json(
            self.request(
                "DELETE",
                f"/cloud/certificates/{certname}",
                json_body={"type": cert_type},
            )
        )

    def update_firmware(self, settings: Mapping[str, Any]) -> Any:
        return _response_json(
            self.request("PUT", "/cloud/os", json_body=dict(settings))
        )

    def revert_firmware(self) -> Any:
        return _response_json(self.request("PUT", "/cloud/revertbackOS"))


class ImpinjR700ReaderManager(ReaderManager):
    """Impinj R700/R720 REST management and inventory-profile adapter."""

    vendor = "impinj"
    models = frozenset({"R700", "R720"})
    capabilities = frozenset(
        {
            "identity",
            "status",
            "mqtt",
            "profiles",
            "inventory_presets",
            "inventory",
            "raw",
        }
    )

    def __init__(
        self,
        base_url: str,
        *,
        model: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 5.0,
        verify_tls: bool = True,
        ca_file: str | None = None,
        cert_file: str | None = None,
        key_file: str | None = None,
    ) -> None:
        super().__init__(model=model)
        self._transport = HTTPReaderManager(
            base_url,
            username=username,
            password=password,
            timeout=timeout,
            verify_tls=verify_tls,
            ca_file=ca_file,
            cert_file=cert_file,
            key_file=key_file,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        data: bytes | str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ReaderHTTPResponse:
        return self._transport.request(
            method, path, json_body=json_body, data=data, headers=headers
        )

    def get_status(self) -> Any:
        return self.request("GET", "/api/v1/status").json()

    def identity(self) -> ReaderIdentity:
        status = self.get_status()
        serial = status.get("serialNumber") if isinstance(status, Mapping) else None
        firmware = status.get("firmwareVersion") if isinstance(status, Mapping) else None
        return ReaderIdentity(self.vendor, self.model, serial, firmware)

    def get_mqtt(self) -> Any:
        return self.request("GET", "/api/v1/mqtt").json()

    def update_mqtt(self, settings: Mapping[str, Any]) -> Any:
        return _response_json(
            self.request("PUT", "/api/v1/mqtt", json_body=dict(settings))
        )

    def get_profiles(self) -> Any:
        return self.request("GET", "/api/v1/profiles").json()

    def get_inventory_presets_schema(self) -> Any:
        return self.request(
            "GET", "/api/v1/profiles/inventory/presets-schema"
        ).json()

    def list_inventory_presets(self) -> Any:
        return self.request("GET", "/api/v1/profiles/inventory/presets").json()

    @staticmethod
    def _preset_path(preset_id: str) -> str:
        if not preset_id or "/" in preset_id or preset_id in {".", ".."}:
            raise ValueError("preset_id must be a non-empty route segment")
        return f"/api/v1/profiles/inventory/presets/{preset_id}"

    def get_inventory_preset(self, preset_id: str) -> Any:
        return self.request("GET", self._preset_path(preset_id)).json()

    def update_inventory_preset(
        self, preset_id: str, settings: Mapping[str, Any]
    ) -> Any:
        return _response_json(
            self.request(
                "PUT", self._preset_path(preset_id), json_body=dict(settings)
            )
        )

    def delete_inventory_preset(self, preset_id: str) -> Any:
        return _response_json(self.request("DELETE", self._preset_path(preset_id)))

    def start_inventory(self, preset_id: str) -> Any:
        path = self._preset_path(preset_id) + "/start"
        return _response_json(self.request("POST", path))

    def stop_inventory(self) -> Any:
        return _response_json(self.request("POST", "/api/v1/profiles/stop"))


class LLRPOnlyReaderManager(ReaderManager):
    """Capability marker for readers managed by LLRP rather than a public REST API."""

    capabilities = frozenset()

    def __init__(self, vendor: str, model: str | None = None) -> None:
        super().__init__(model=model)
        self.vendor = vendor


def create_reader_manager(
    vendor: str,
    model: str,
    base_url: str | None = None,
    **kwargs: Any,
) -> ReaderManager:
    """Create the appropriate vendor management adapter.

    Readers without a documented HTTP management contract return an
    :class:`LLRPOnlyReaderManager` instead of silently guessing web endpoints.
    """
    if not vendor or not model:
        raise ValueError("vendor and model are required")

    normalized_vendor = vendor.strip().lower()
    normalized_model = model.strip().upper().replace(" ", "")

    if normalized_vendor in {"zebra", "motorola"}:
        zebra_model = normalized_model.replace("-", "")
        if zebra_model.startswith("FXR90"):
            zebra_model = "FXR90"
        if zebra_model in {"FX7500", "FX9600", "ATR7000", "FXR90"}:
            if base_url is None:
                raise ValueError("base_url is required for Zebra REST management")
            return ZebraReaderManager(base_url, model=zebra_model, **kwargs)
        return LLRPOnlyReaderManager(normalized_vendor, model)

    if normalized_vendor == "impinj":
        if normalized_model in {"R700", "R720"}:
            if base_url is None:
                raise ValueError("base_url is required for Impinj REST management")
            return ImpinjR700ReaderManager(base_url, model=normalized_model, **kwargs)
        return LLRPOnlyReaderManager("impinj", model)

    return LLRPOnlyReaderManager(normalized_vendor, model)
