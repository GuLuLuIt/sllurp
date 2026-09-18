"""Zebra fixed-reader management adapters.

Zebra fixed readers expose two documented management families:

* Reader Management (RM) XML over HTTP/HTTPS on FX7400/FX7500/FX9500/
  FX9600/ATR7000.
* Zebra IoT Connector local REST APIs on supported modern firmware,
  including FX7500/FX9600/ATR7000 and FXR90-family readers.

These adapters sit on top of :mod:`sllurp.reader_management` so LLRP inventory
and out-of-band reader administration remain separate.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from xml.etree import ElementTree as ET  # nosec B405 -- construction only

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring as safe_fromstring

from .reader_management import (
    HTTPReaderManager,
    ReaderManagementError,
    UnsupportedReaderOperation,
)

RM_NS = "urn:epcglobal:rm:xsd:1"
EPC_NS = "urn:epcglobal:xsd:1"
MOTOR_NS = "urn:motorfid:rm:xsd:1"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

for _prefix, _uri in (
    ("rm", RM_NS),
    ("epcglobal", EPC_NS),
    ("motorm", MOTOR_NS),
    ("xsi", XSI_NS),
):
    ET.register_namespace(_prefix, _uri)

RM_MODELS = frozenset({"FX7400", "FX7500", "FX9500", "FX9600", "ATR7000"})
IOT_MODELS = frozenset({"FX7500", "FX9600", "ATR7000", "FXR90"})

# Zebra's RM product matrix explicitly marks these operations unsupported on
# FX9500.  Keep the common API, but fail before sending an invalid command.
_FX9500_UNSUPPORTED = frozenset(
    {
        "setFirmwareUpdateParams",
        "getSupportedRegionList",
        "getRegionStandardList",
        "setNetworkInterfaceSettings",
        "setDHCPConfig",
        "setActiveRegion",
        "setShellStatus",
        "setFTPStatus",
        "discardConfigChanges",
        "hasConfigChanged",
        "getUncommitedConfigChangesDescription",
        "importProfileToReader",
        "exportProfileFromReader",
    }
)


def _model_name(model: str) -> str:
    value = model.strip().upper().replace("-", "")
    return "FXR90" if value.startswith("FXR90") else value


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def _element_value(element: ET.Element) -> Any:
    children = list(element)
    if not children:
        return (element.text or "").strip()
    result: dict[str, Any] = {}
    for child in children:
        key = _local_name(child.tag)
        value = _element_value(child)
        if key in result:
            current = result[key]
            if not isinstance(current, list):
                result[key] = [current]
            result[key].append(value)
        else:
            result[key] = value
    return result


def _find_text(root: ET.Element, name: str) -> str | None:
    for element in root.iter():
        if _local_name(element.tag) == name:
            return (element.text or "").strip()
    return None


class ZebraRMManager:
    """Zebra Reader Management XML/HTTP(S) client.

    This is the management interface for the FX9500 and is also available on
    multiple other Zebra fixed-reader generations.  Commands use Zebra's
    documented ``/control`` endpoint and authenticated RM sessions.
    """

    def __init__(
        self,
        base_url: str,
        *,
        username: str,
        password: str,
        model: str,
        target_name: str = "Reader",
        timeout: float = 5.0,
        verify_tls: bool = True,
        ca_file: str | None = None,
        cert_file: str | None = None,
        key_file: str | None = None,
    ) -> None:
        self.model = _model_name(model)
        if self.model not in RM_MODELS:
            raise ValueError(f"{model!r} is not a supported Zebra RM model")
        self.username = username
        self.password = password
        self.target_name = target_name
        self.session_id: str | None = None
        self._command_id = 0
        self.transport = HTTPReaderManager(
            base_url,
            timeout=timeout,
            verify_tls=verify_tls,
            ca_file=ca_file,
            cert_file=cert_file,
            key_file=key_file,
        )

    def _next_id(self) -> str:
        self._command_id += 1
        return str(self._command_id)

    def _require(self, command: str) -> None:
        if self.model == "FX9500" and command in _FX9500_UNSUPPORTED:
            raise UnsupportedReaderOperation(
                f"Zebra {self.model} does not support RM command ReaderDevice.{command}"
            )

    def _xml(
        self,
        command: str,
        params: Mapping[str, Any] | None,
        *,
        require_session: bool,
    ) -> bytes:
        root = ET.Element(
            f"{{{RM_NS}}}command",
            {
                f"{{{EPC_NS}}}creationDate": "2001-12-17T09:30:47.0Z",
                f"{{{EPC_NS}}}schemaVersion": "0.0",
                f"{{{XSI_NS}}}schemaLocation": "urn:epcglobal:rm:xsd:1 RmCommand.xsd",
            },
        )
        ET.SubElement(root, f"{{{RM_NS}}}id").text = self._next_id()
        ET.SubElement(root, f"{{{RM_NS}}}targetName").text = self.target_name
        device = ET.SubElement(root, f"{{{MOTOR_NS}}}readerDevice")
        if require_session:
            if not self.session_id:
                raise ReaderManagementError(
                    "Zebra RM login is required before this command"
                )
            ET.SubElement(device, f"{{{MOTOR_NS}}}sessionID").text = self.session_id
        operation = ET.SubElement(device, f"{{{MOTOR_NS}}}{command}")

        def append_value(parent: ET.Element, key: str, value: Any) -> None:
            if isinstance(value, (list, tuple)):
                for item in value:
                    append_value(parent, key, item)
                return
            child = ET.SubElement(parent, f"{{{MOTOR_NS}}}{key}")
            if isinstance(value, Mapping):
                for nested_key, nested_value in value.items():
                    append_value(child, str(nested_key), nested_value)
            else:
                child.text = _text_value(value)

        for key, value in (params or {}).items():
            append_value(operation, str(key), value)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def command(
        self,
        name: str,
        params: Mapping[str, Any] | None = None,
        *,
        require_session: bool = True,
    ) -> Any:
        """Execute a Zebra RM ``ReaderDevice`` command and return its payload."""
        self._require(name)
        payload = self._xml(name, params, require_session=require_session)
        response = self.transport.request(
            "GET",
            "/control",
            data=payload,
            headers={
                "Content-Type": "application/xml",
                "Accept": "application/xml",
            },
        )
        try:
            root = safe_fromstring(response.body)
        except (ET.ParseError, DefusedXmlException) as exc:
            raise ReaderManagementError(
                "reader returned invalid RM XML", body=response.body
            ) from exc
        result_code = _find_text(root, "resultCode")
        if result_code not in {None, "0"}:
            detail = _find_text(root, "resultDescription") or _find_text(
                root, "errorDescription"
            )
            suffix = f": {detail}" if detail else ""
            raise ReaderManagementError(
                f"Zebra RM command {name} failed with resultCode {result_code}{suffix}",
                body=response.body,
            )
        operation = next(
            (element for element in root.iter() if _local_name(element.tag) == name),
            None,
        )
        return _element_value(operation) if operation is not None else _element_value(root)

    def login(self, *, force: bool = True) -> str:
        """Open a Reader Management session and return its session identifier."""
        result = self.command(
            "doLogin",
            {
                "username": self.username,
                "password": self.password,
                "forceLogin": force,
            },
            require_session=False,
        )
        session = result.get("sessionID") if isinstance(result, dict) else None
        if not session:
            raise ReaderManagementError(
                "Zebra RM login response did not contain a sessionID"
            )
        self.session_id = str(session).strip()
        return self.session_id

    def logout(self, *, force: bool = False) -> Any:
        """Close the active Reader Management session and return vendor data."""
        try:
            return self.command("doLogout", {"forceLogout": force})
        finally:
            self.session_id = None

    def get_info(self) -> dict[str, Any]:
        """Return normalized reader identity and firmware information."""
        return {
            "manufacturer": self.command("getManufacturer"),
            "model": self.command("getModel"),
            "name": self.command("getName"),
            "version": self.command("getReaderVersionInfo"),
        }

    def get_status(self) -> dict[str, Any]:
        """Return normalized reader status information."""
        return {
            "cpu": self.command("getCPUUsage"),
            "ram": self.command("getRAMUsage"),
            "details": self.command("getReaderDetails"),
        }

    def get_network(self, interface: str = "ETH", *, core: bool = True) -> Any:
        """Return network settings for ``interface`` from the reader."""
        return self.command(
            "getNetworkInterfaceSettings",
            {"Interface": interface, "isCoreConfig": core},
        )

    def set_network(self, **settings: Any) -> Any:
        """Apply vendor network-setting fields and return the decoded result."""
        return self.command("setNetworkInterfaceSettings", settings)

    def set_dhcp(
        self,
        interface: str = "ETH",
        *,
        enabled: bool = True,
        ipv6: bool = False,
    ) -> Any:
        """Enable or disable IPv4/IPv6 DHCP for one interface."""
        return self.command(
            "setDHCPConfig",
            {
                "Interface": interface,
                "enableDHCP": enabled,
                "enableDHCPv6": ipv6,
            },
        )

    def get_supported_regions(self) -> Any:
        """Return the regulatory regions supported by the reader."""
        return self.command("getSupportedRegionList")

    def get_region_standards(
        self, region_name: str, *, include_channels: bool = True
    ) -> Any:
        """Return standards, optionally with channels, for a regulatory region."""
        return self.command(
            "getRegionStandardList",
            {
                "regionName": region_name,
                "requestChannelList": include_channels,
            },
        )

    def get_region(self) -> Any:
        """Return the active regulatory region configuration."""
        return self.command("getActiveRegion")

    def set_region(
        self,
        region_name: str,
        standard_name: str,
        channels: list[int] | tuple[int, ...],
        *,
        lbt: bool = False,
        hopping: bool = False,
    ) -> Any:
        """Set regulatory region, standard, channels, LBT, and hopping values."""
        return self.command(
            "setActiveRegion",
            {
                "regionName": region_name,
                "standardName": standard_name,
                "channelUsed": channels,
                "doLBT": lbt,
                "doHopping": hopping,
            },
        )

    def get_llrp_config(self) -> Any:
        """Return the reader's LLRP transport configuration."""
        return self.command("getLLRPConfig")

    def set_llrp_config(
        self,
        *,
        port: int,
        secure: bool,
        validate_peer: bool,
        client: bool,
        server_ip: str = "",
        reconnect: bool = False,
    ) -> Any:
        """Set LLRP port, security, peer validation, and client/server mode."""
        return self.command(
            "setLLRPConfig",
            {
                "portNum": port,
                "IsSecure": secure,
                "ValidatePeerInSecureMode": validate_peer,
                "IsClient": client,
                "serverIP": server_ip,
                "ShouldReconnect": reconnect,
            },
        )

    def reboot(self, *, force: bool = True) -> Any:
        """Request a reader reboot and return the decoded acknowledgement."""
        return self.command(
            "shutDown", {"restartNeeded": True, "forceShutdown": force}
        )

    def shutdown(self, *, force: bool = False) -> Any:
        """Request reader shutdown and return the decoded acknowledgement."""
        return self.command(
            "shutDown", {"restartNeeded": False, "forceShutdown": force}
        )

    def save_config(self) -> Any:
        """Persist staged reader configuration and return vendor data."""
        return self.command("saveConfigChanges")

    def discard_config(self) -> Any:
        """Discard staged reader configuration and return vendor data."""
        return self.command("discardConfigChanges")

    def has_config_changed(self) -> Any:
        """Return the vendor indication of unsaved configuration changes."""
        return self.command("hasConfigChanged")

    def get_config_changes_description(self) -> Any:
        """Return the vendor description of staged configuration changes."""
        return self.command("getUncommitedConfigChangesDescription")

    def set_name(self, name: str) -> Any:
        """Set the reader's display name and return vendor data."""
        return self.command("setName", {"name": name})

    def get_max_antennas(self) -> Any:
        """Return the reader-reported maximum antenna count."""
        return self.command("getMaxAntennasSupported")

    def get_read_points(
        self, *, maintenance_mode: bool = False, refresh_interval: int = 0
    ) -> Any:
        """Return antenna/read-point information from the reader."""
        return self.command(
            "getAllReadPoints",
            {
                "maintenanceMode": maintenance_mode,
                "refreshInterval": refresh_interval,
            },
        )

    def get_profiles(self) -> Any:
        """Return the reader's saved configuration profiles."""
        return self.command("getReaderProfileList")

    def activate_profile(self, name: str) -> Any:
        """Activate a saved configuration profile by name."""
        return self.command("setProfileActive", {"ProfileName": name})

    def delete_profile(self, name: str) -> Any:
        """Delete a saved configuration profile by name."""
        return self.command("deleteProfile", {"ProfileName": name})

    def import_profile(
        self,
        name: str,
        data: str,
        *,
        set_active: bool = False,
        save: bool = True,
        force_overwrite: bool = False,
    ) -> Any:
        """Import profile text with activation, save, and overwrite controls."""
        return self.command(
            "importProfileToReader",
            {
                "ProfileName": name,
                "ProfileData": data,
                "doSetActive": set_active,
                "doSaveChange": save,
                "doForceOverwrite": force_overwrite,
            },
        )

    def export_profile(self, name: str) -> Any:
        """Return the exported representation of a saved profile."""
        return self.command("exportProfileFromReader", {"ProfileName": name})

    def get_time(self) -> Any:
        """Return the reader's current date/time configuration."""
        return self.command("getLocalTime")

    def set_time(self, date_time: str) -> Any:
        """Set the reader time using the vendor's date-time string format."""
        return self.command("setLocalTime", {"dateTime": date_time})

    def get_time_zones(self) -> Any:
        """Return the time zones known to the reader."""
        return self.command("getTimeZones")

    def set_time_zone(self, time_zone_index: int) -> Any:
        """Select a reader time zone by vendor index."""
        return self.command("setTimeZone", {"timeZoneIndex": time_zone_index})

    def get_shell_status(self) -> Any:
        """Return the reader shell-service status."""
        return self.command("getShellStatus")

    def set_shell_status(self, state: str) -> Any:
        """Set the reader shell-service state."""
        return self.command("setShellStatus", {"shellState": state})

    def get_ftp_status(self) -> Any:
        """Return the reader FTP-service status."""
        return self.command("getFTPStatus")

    def set_ftp_status(self, state: str) -> Any:
        """Set the reader FTP-service state."""
        return self.command("setFTPStatus", {"ftpState": state})

    def get_ext_antenna_mode(self) -> Any:
        """Return the external-antenna operating mode."""
        return self.command("getExtAntennaMode")

    def set_ext_antenna_mode(self, mode: Any) -> Any:
        """Set the external-antenna operating mode."""
        return self.command("setExtAntennaMode", {"extAntennaMode": mode})

    def configure_firmware_update(
        self,
        image_url: str,
        *,
        username: str = "",
        password: str = "",
        update_all_partitions: bool = True,
    ) -> Any:
        """Stage a firmware-image URL and optional download credentials."""
        return self.command(
            "setFirmwareUpdateParams",
            {
                "imageLocationURL": image_url,
                "userName": username,
                "password": password,
                "updateAllPartitions": update_all_partitions,
            },
        )

    def start_firmware_update(self) -> Any:
        """Start the previously configured firmware update."""
        return self.command("doFirmwareUpdate")

    def get_debounce_time(self) -> Any:
        """Return the configured input debounce time."""
        return self.command("getDebounceTime")

    def set_debounce_time(self, milliseconds: int) -> Any:
        """Set input debounce time in milliseconds."""
        return self.command("setDebounceTime", {"dbtime": milliseconds})

    def change_password(
        self, username: str, old_password: str, new_password: str
    ) -> Any:
        """Change a reader account password using the current password."""
        return self.command(
            "doChangePassword",
            {
                "userName": username,
                "oldPassword": old_password,
                "newPassword": new_password,
            },
        )


class ZebraIoTConnectorManager:
    """Zebra IoT Connector local REST management client."""

    def __init__(
        self,
        base_url: str,
        *,
        model: str,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        timeout: float = 5.0,
        verify_tls: bool = True,
        ca_file: str | None = None,
        cert_file: str | None = None,
        key_file: str | None = None,
    ) -> None:
        self.model = _model_name(model)
        if self.model not in IOT_MODELS:
            raise ValueError(
                f"{model!r} is not a supported Zebra IoT Connector model"
            )
        if token and (username is not None or password is not None):
            raise ValueError("token cannot be combined with username/password")
        if not token and ((username is None) != (password is None)):
            raise ValueError("username and password must be supplied together")
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = token
        self._transport_options = {
            "timeout": timeout,
            "verify_tls": verify_tls,
            "ca_file": ca_file,
            "cert_file": cert_file,
            "key_file": key_file,
        }
        self.transport = self._new_transport(token=token)

    def _new_transport(
        self, *, token: str | None = None, basic: bool = False
    ) -> HTTPReaderManager:
        credentials: dict[str, Any] = {}
        if token:
            credentials["bearer_token"] = token
        elif basic:
            credentials.update(username=self.username, password=self.password)
        return HTTPReaderManager(
            self.base_url, **credentials, **self._transport_options
        )

    def login(self) -> str:
        """Authenticate and return the IoT Connector access token."""
        if self.username is None:
            if self.token:
                return self.token
            raise ReaderManagementError(
                "username/password or a bearer token is required"
            )
        response = self._new_transport(basic=True).request(
            "GET", "/cloud/localRestLogin"
        )
        text = response.text.strip()
        token: str | None = None
        try:
            decoded = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            decoded = None
        if isinstance(decoded, dict):
            for key in ("token", "jwt", "access_token", "JWT Token"):
                if decoded.get(key):
                    token = str(decoded[key]).strip()
                    break
        if not token and text:
            token = (
                text.split("JWT Token:", 1)[-1].strip()
                if "JWT Token:" in text
                else text
            )
        if not token:
            raise ReaderManagementError(
                "Zebra localRestLogin response did not contain a token",
                body=response.body,
            )
        self.token = token
        self.transport = self._new_transport(token=token)
        return token

    def _ensure_auth(self) -> None:
        if not self.token:
            self.login()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        data: bytes | str | None = None,
    ) -> Any:
        """Send an authenticated IoT Connector request.

        This is also the escape hatch for documented endpoints that do not yet
        have a convenience method.
        """
        self._ensure_auth()
        response = self.transport.request(
            method, path, json_body=json_body, data=data
        )
        if not response.body:
            return None
        content_type = response.headers.get("Content-Type", "")
        if "json" in content_type.lower() or response.body.lstrip().startswith(
            (b"{", b"[")
        ):
            return response.json()
        return response.text

    def get_info(self) -> Any:
        """Return reader identity information as decoded JSON."""
        return self.request("GET", "/cloud/version")

    def get_status(self) -> Any:
        """Return IoT Connector status as decoded JSON."""
        return self.request("GET", "/cloud/status")

    def get_capabilities(self) -> Any:
        """Return IoT Connector capability data."""
        return self.request("GET", "/cloud/readerCapabilities")

    def get_network(self, interface: str | None = None) -> Any:
        """Return all network settings or settings for one interface."""
        body = {"interface": interface} if interface else None
        return self.request("GET", "/cloud/network", json_body=body)

    def set_network(self, settings: Mapping[str, Any]) -> Any:
        """Apply the supplied network-settings mapping."""
        return self.request("PUT", "/cloud/network", json_body=dict(settings))

    def get_hostname(self) -> Any:
        """Return the reader hostname configuration."""
        return self.request("GET", "/cloud/hostname")

    def set_hostname(self, hostname: str) -> Any:
        """Set the reader hostname."""
        return self.request(
            "PUT", "/cloud/hostname", json_body={"hostname": hostname}
        )

    def get_region(self) -> Any:
        """Return the active regulatory region."""
        return self.request("GET", "/cloud/region")

    def get_supported_regions(self) -> Any:
        """Return regulatory regions supported by the reader."""
        return self.request("GET", "/cloud/supportedRegionList")

    def get_config(self) -> Any:
        """Return the IoT Connector configuration."""
        return self.request("GET", "/cloud/config")

    def set_config(self, config: Mapping[str, Any]) -> Any:
        """Replace/update the IoT Connector configuration mapping."""
        return self.request("PUT", "/cloud/config", json_body=dict(config))

    def get_mode(self, *, verbose: bool = False) -> Any:
        """Return the operating mode, optionally with verbose detail."""
        return self.request(
            "GET", "/cloud/mode", json_body={"verbose": verbose}
        )

    def set_mode(self, mode: Mapping[str, Any]) -> Any:
        """Set the operating-mode configuration."""
        return self.request("PUT", "/cloud/mode", json_body=dict(mode))

    def start(self, *, persist_state: bool = False) -> Any:
        """Start IoT Connector, optionally persisting the running state."""
        return self.request(
            "PUT",
            "/cloud/start",
            json_body={"doNotPersistState": not persist_state},
        )

    def stop(self) -> Any:
        """Stop IoT Connector and return the decoded response."""
        return self.request("PUT", "/cloud/stop")

    def reboot(self) -> Any:
        """Request a reader reboot."""
        return self.request("PUT", "/cloud/reboot")

    def get_gpi(self) -> Any:
        """Return general-purpose input states."""
        return self.request("GET", "/cloud/gpi")

    def get_gpo(self) -> Any:
        """Return general-purpose output states."""
        return self.request("GET", "/cloud/gpo")

    def set_gpo(self, port: int, state: bool) -> Any:
        """Set one general-purpose output port to a boolean state."""
        return self.request(
            "PUT", "/cloud/gpo", json_body={"port": port, "state": state}
        )

    def set_time_zone(self, time_zone: str) -> Any:
        """Set the reader time zone using the vendor string format."""
        return self.request(
            "PUT", "/cloud/timeZone", json_body={"timeZone": time_zone}
        )

    def update_firmware(self, settings: Mapping[str, Any]) -> Any:
        """Submit firmware-update settings and return the decoded response."""
        return self.request("PUT", "/cloud/os", json_body=dict(settings))


def zebra_reader_manager(
    model: str,
    base_url: str,
    *,
    api: str = "auto",
    **kwargs: Any,
) -> ZebraRMManager | ZebraIoTConnectorManager:
    """Create the appropriate Zebra management adapter for a reader model.

    ``auto`` chooses RM for FX7400/FX7500/FX9500/FX9600/ATR7000 because RM is
    broadly available across their firmware generations, and IoT Connector for
    FXR90.  Pass ``api='iot'`` explicitly for modern IoT Connector firmware on
    FX7500/FX9600/ATR7000.
    """
    normalized = _model_name(model)
    choice = api.lower()
    if choice == "auto":
        choice = "iot" if normalized == "FXR90" else "rm"
    if choice == "rm":
        return ZebraRMManager(base_url, model=normalized, **kwargs)
    if choice == "iot":
        return ZebraIoTConnectorManager(base_url, model=normalized, **kwargs)
    raise ValueError("api must be 'auto', 'rm', or 'iot'")

