"""Zebra IoT Connector Local REST API client.

This module is intentionally separate from the LLRP client. Zebra fixed RFID
readers expose the IoT Connector Local REST interface for out-of-band reader
management and control while LLRP remains available for normal RFID workflows.
"""

from __future__ import annotations

import base64
import json
import ssl
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ZebraIoTConnectorError(RuntimeError):
    """Raised when a Zebra IoT Connector REST request fails."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        body: Any = None,
        url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.body = body
        self.url = url


class ZebraIoTAuthenticationError(ZebraIoTConnectorError):
    """Raised when Local REST authentication is missing or invalid."""


def _decode_response(body: bytes) -> Any:
    if not body:
        return None
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _extract_token(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("token", "jwtToken", "jwt", "JWT Token", "access_token"):
            token = value.get(key)
            if token:
                return str(token).strip()
        return None
    if not isinstance(value, str):
        return None
    token = value.strip()
    prefix = "JWT Token:"
    if token.startswith(prefix):
        token = token[len(prefix) :].strip()
    return token or None


class ZebraIoTConnectorClient:
    """Client for the Zebra IoT Connector Local REST API.

    ``base_url`` may be a complete HTTP(S) URL or a reader hostname/IP. When no
    scheme is supplied, HTTPS is used. Call :meth:`login` before authenticated
    management/control operations, or supply an existing bearer ``token``.
    """

    def __init__(
        self,
        base_url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        timeout: float = 5.0,
        verify_tls: bool = True,
        ca_file: str | None = None,
    ) -> None:
        base_url = base_url.strip()
        if "://" not in base_url:
            base_url = f"https://{base_url}"
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = token
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.ca_file = ca_file

    def _ssl_context(self) -> ssl.SSLContext | None:
        if not self.base_url.lower().startswith("https://"):
            return None
        context = ssl.create_default_context(cafile=self.ca_file)
        if not self.verify_tls:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        *,
        authenticated: bool = True,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Call any IoT Connector Local REST endpoint and decode its response."""
        request_headers = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)

        if authenticated:
            if not self.token:
                raise ZebraIoTAuthenticationError(
                    "IoT Connector bearer token is not set; call login() first"
                )
            request_headers["Authorization"] = f"Bearer {self.token}"

        data = None
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")

        url = self._url(path)
        request = Request(
            url,
            data=data,
            headers=request_headers,
            method=method.upper(),
        )
        try:
            with urlopen(
                request,
                timeout=self.timeout,
                context=self._ssl_context(),
            ) as response:
                return _decode_response(response.read())
        except HTTPError as exc:
            body = _decode_response(exc.read())
            raise ZebraIoTConnectorError(
                f"{method.upper()} {path} failed with HTTP {exc.code}",
                status=exc.code,
                body=body,
                url=url,
            ) from exc
        except URLError as exc:
            raise ZebraIoTConnectorError(
                f"{method.upper()} {path} failed: {exc.reason}",
                url=url,
            ) from exc

    def login(self) -> str:
        """Authenticate with reader web-console credentials and store the JWT."""
        if self.username is None or self.password is None:
            raise ZebraIoTAuthenticationError(
                "username and password are required for IoT Connector login"
            )
        credentials = f"{self.username}:{self.password}".encode("utf-8")
        basic = base64.b64encode(credentials).decode("ascii")
        result = self.request(
            "GET",
            "/cloud/localRestLogin",
            authenticated=False,
            headers={"Authorization": f"Basic {basic}"},
        )
        token = _extract_token(result)
        if not token:
            raise ZebraIoTAuthenticationError(
                "IoT Connector login response did not contain a JWT token",
                body=result,
            )
        self.token = token
        return token

    def clear_token(self) -> None:
        """Discard the locally cached bearer token."""
        self.token = None

    # Management interface convenience methods.
    def get_version(self) -> Any:
        return self.request("GET", "/cloud/version")

    def get_hostname(self) -> Any:
        return self.request("GET", "/cloud/hostname")

    def set_hostname(self, hostname: str) -> Any:
        return self.request("PUT", "/cloud/hostname", {"hostname": hostname})

    def get_network(self, interface: str = "all") -> Any:
        return self.request("GET", "/cloud/network", {"interface": interface})

    def set_network(self, config: Mapping[str, Any]) -> Any:
        return self.request("PUT", "/cloud/network", dict(config))

    def get_config(self) -> Any:
        return self.request("GET", "/cloud/config")

    def set_config(self, config: Mapping[str, Any]) -> Any:
        return self.request("PUT", "/cloud/config", dict(config))

    def reboot(self) -> Any:
        return self.request("PUT", "/cloud/reboot")

    def get_name_and_description(self) -> Any:
        return self.request("GET", "/cloud/nameAndDescription")

    def set_name_and_description(self, name: str, description: str) -> Any:
        return self.request(
            "PUT",
            "/cloud/nameAndDescription",
            {"name": name, "description": description},
        )

    def set_gpo(self, port: int, state: bool) -> Any:
        if not 1 <= port <= 4:
            raise ValueError("GPO port must be between 1 and 4")
        return self.request("PUT", "/cloud/gpo", {"port": port, "state": state})

    # Control interface convenience methods.
    def get_mode(self, *, verbose: bool = False) -> Any:
        return self.request("GET", "/cloud/mode", {"verbose": verbose})

    def set_mode(self, mode: Mapping[str, Any]) -> Any:
        return self.request("PUT", "/cloud/mode", dict(mode))

    def start(self, *, do_not_persist_state: bool = True) -> Any:
        return self.request(
            "PUT",
            "/cloud/start",
            {"doNotPersistState": do_not_persist_state},
        )

    def stop(self) -> Any:
        return self.request("PUT", "/cloud/stop")
