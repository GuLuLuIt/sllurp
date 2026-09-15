import base64
import io
import json
from urllib.error import HTTPError

import pytest

import sllurp.zebra_iot as zebra_iot
from sllurp.zebra_iot import (
    ZebraIoTAuthenticationError,
    ZebraIoTConnectorClient,
    ZebraIoTConnectorError,
)


class FakeResponse:
    def __init__(self, body=b"{}"):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_login_uses_basic_auth_and_caches_jwt(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout, context):
        seen["request"] = request
        seen["timeout"] = timeout
        return FakeResponse(b"JWT Token: synthetic-token")

    monkeypatch.setattr(zebra_iot, "urlopen", fake_urlopen)
    client = ZebraIoTConnectorClient(
        "reader.invalid", username="synthetic-user", password="synthetic-secret"
    )

    assert client.login() == "synthetic-token"
    assert client.token == "synthetic-token"
    request = seen["request"]
    expected = base64.b64encode(
        b"synthetic-user:synthetic-secret"
    ).decode("ascii")
    assert request.full_url == "https://reader.invalid/cloud/localRestLogin"
    assert request.get_method() == "GET"
    assert request.get_header("Authorization") == f"Basic {expected}"


def test_set_hostname_uses_bearer_auth_and_documented_payload(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout, context):
        seen["request"] = request
        return FakeResponse(b'{"ok":true}')

    monkeypatch.setattr(zebra_iot, "urlopen", fake_urlopen)
    client = ZebraIoTConnectorClient("reader.invalid", token="synthetic-token")

    assert client.set_hostname("synthetic-reader") == {"ok": True}
    request = seen["request"]
    assert request.get_method() == "PUT"
    assert request.get_header("Authorization") == "Bearer synthetic-token"
    assert json.loads(request.data) == {"hostname": "synthetic-reader"}


def test_start_uses_documented_persistence_flag(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout, context):
        seen["request"] = request
        return FakeResponse()

    monkeypatch.setattr(zebra_iot, "urlopen", fake_urlopen)
    client = ZebraIoTConnectorClient("reader.invalid", token="synthetic-token")
    client.start(do_not_persist_state=False)

    request = seen["request"]
    assert request.full_url == "https://reader.invalid/cloud/start"
    assert json.loads(request.data) == {"doNotPersistState": False}


def test_authenticated_request_requires_token():
    client = ZebraIoTConnectorClient("reader.invalid")
    with pytest.raises(ZebraIoTAuthenticationError, match="call login"):
        client.get_version()


def test_http_error_exposes_status_and_decoded_body(monkeypatch):
    def fake_urlopen(request, timeout, context):
        raise HTTPError(
            request.full_url,
            401,
            "Unauthorized",
            {},
            io.BytesIO(b'{"error":"denied"}'),
        )

    monkeypatch.setattr(zebra_iot, "urlopen", fake_urlopen)
    client = ZebraIoTConnectorClient("reader.invalid", token="synthetic-token")

    with pytest.raises(ZebraIoTConnectorError) as exc_info:
        client.get_version()
    assert exc_info.value.status == 401
    assert exc_info.value.body == {"error": "denied"}


def test_gpo_port_is_validated_before_request():
    client = ZebraIoTConnectorClient("reader.invalid", token="synthetic-token")
    with pytest.raises(ValueError, match="between 1 and 4"):
        client.set_gpo(5, True)
