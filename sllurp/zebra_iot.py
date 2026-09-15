"""Zebra IoT Connector Local REST client.

This module implements the documented Local REST authentication and a small
set of common management/control endpoints for Zebra fixed RFID readers.
Endpoint availability depends on reader model and firmware.
"""

from __future__ import annotations

import base64
import json
import ssl
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import ParseResult, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener


class ZebraIoTError(RuntimeError):
    """Raised when a Zebra IoT Connector request fails."""

    def __init__(self, message: str, *, status: int | None = None, body: bytes | None = None):
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass(frozen=True)
class ZebraIoTResponse:
    """Normalized Local REST response."""

    status: int
    headers: Mapping[str, str]
    body: bytes

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        if not self.body:
            return None
        return json.loads(self.body.decode("utf-8"))


def _origin(parsed: ParseResult) -> tuple[str, str, int]:
    if parsed.hostname is None:
        raise ValueError("URL must include a hostname")
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme.lower() == "https" else 80
    return parsed.scheme.lower(), parsed.hostname.casefold(), port


class _SameOriginRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed_origin: tuple[str, str, int]) -> None:
        super().__init__()
        self.allowed_origin = allowed_origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or _origin(parsed) != self.allowed_origin
        ):
            raise ZebraIoTError("redirect left the configured reader host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class ZebraIoTConnector:
    """Client for Zebra IoT Connector Local REST APIs.

    ``username``/``password`` are used only for ``/cloud/localRestLogin``.
    The returned JWT is then sent as a bearer token for subsequent requests.
    A previously obtained token can be supplied directly with ``token``.
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
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an absolute http:// or https:// URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("base_url must not contain embedded credentials")
        if token and (username is not None or password is not None):
            raise ValueError("token cannot be combined with username/password")
        if (username is None) != (password is None):
            raise ValueError("username and password must be supplied together")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.base_url = base_url.rstrip("/") + "/"
        self.username = username
        self.password = password
        self.token = token
        self.timeout = float(timeout)
        self._base_origin = _origin(parsed)

        handlers = [_SameOriginRedirectHandler(self._base_origin)]
        if parsed.scheme == "https":
            if verify_tls:
                context = ssl.create_default_context(cafile=ca_file)
            else:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            handlers.append(HTTPSHandler(context=context))
        self._opener = build_opener(*handlers)

    def _url(self, path: str) -> str:
        parsed = urlparse(path)
        if parsed.scheme or parsed.netloc:
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("path URL must use absolute http:// or https://")
            if parsed.username is not None or parsed.password is not None:
                raise ValueError("path URL must not contain embedded credentials")
            if _origin(parsed) != self._base_origin:
                raise ValueError("requests must stay on the configured reader host")
            return path
        return urljoin(self.base_url, path.lstrip("/"))

    def _send(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ZebraIoTResponse:
        request = Request(
            self._url(path),
            data=body,
            headers=dict(headers or {}),
            method=method.upper(),
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                return ZebraIoTResponse(
                    response.status,
                    dict(response.headers.items()),
                    response.read(),
                )
        except HTTPError as exc:
            with exc:
                error_body = exc.read()
            raise ZebraIoTError(
                f"reader returned HTTP {exc.code} {exc.reason}",
                status=exc.code,
                body=error_body,
            ) from exc
        except (URLError, OSError, TimeoutError) as exc:
            raise ZebraIoTError(f"reader request failed: {exc}") from exc

    def login(self) -> str:
        """Authenticate with Basic auth and return the Local REST JWT."""
        if self.token:
            return self.token
        if self.username is None:
            raise ZebraIoTError("username/password or token is required")

        credentials = f"{self.username}:{self.password}".encode("utf-8")
        basic = base64.b64encode(credentials).decode("ascii")
        response = self._send(
            "GET",
            "/cloud/localRestLogin",
            headers={"Authorization": f"Basic {basic}"},
        )
        text = response.text.strip()
        token = None
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
            token = text.split("JWT Token:", 1)[-1].strip() if "JWT Token:" in text else text
        if not token:
            raise ZebraIoTError("localRestLogin response did not contain a token", body=response.body)
        self.token = token
        return token

    def request(self, method: str, path: str, *, json_body: Any = None) -> Any:
        """Send an authenticated Local REST request.

        This also provides access to documented endpoints that do not have a
        convenience method yet.
        """
        token = self.login()
        headers = {"Authorization": f"Bearer {token}"}
        body = None
        if json_body is not None:
            body = json.dumps(json_body, separators=(",", ":")).encode("utf-8")
            headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        response = self._send(method, path, body=body, headers=headers)
        if not response.body:
            return None
        content_type = response.headers.get("Content-Type", "")
        if "json" in content_type.lower() or response.body.lstrip().startswith((b"{", b"[")):
            return response.json()
        return response.text

    def get_version(self) -> Any:
        return self.request("GET", "/cloud/version")

    def get_status(self) -> Any:
        return self.request("GET", "/cloud/status")

    def get_capabilities(self) -> Any:
        return self.request("GET", "/cloud/readerCapabilities")

    def get_hostname(self) -> Any:
        return self.request("GET", "/cloud/hostname")

    def set_hostname(self, hostname: str) -> Any:
        return self.request("PUT", "/cloud/hostname", json_body={"hostname": hostname})

    def get_config(self) -> Any:
        return self.request("GET", "/cloud/config")

    def set_config(self, config: Mapping[str, Any]) -> Any:
        return self.request("PUT", "/cloud/config", json_body=dict(config))

    def start(self, *, do_not_persist_state: bool = True) -> Any:
        return self.request(
            "PUT",
            "/cloud/start",
            json_body={"doNotPersistState": do_not_persist_state},
        )

    def stop(self) -> Any:
        return self.request("PUT", "/cloud/stop")
