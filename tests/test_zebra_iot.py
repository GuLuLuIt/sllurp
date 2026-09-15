import base64
import json

import pytest

from sllurp.zebra_iot import ZebraIoTConnector


class FakeResponse:
    def __init__(self, body=b"", *, status=200, headers=None):
        self.status = status
        self.headers = headers or {}
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


class FakeOpener:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        return self.responses.pop(0)


def test_login_then_authenticated_version_request():
    client = ZebraIoTConnector(
        "https://reader.example", username="admin", password="secret"
    )
    opener = FakeOpener(
        FakeResponse(b"JWT Token: synthetic-token"),
        FakeResponse(
            b'{"model":"FX9600"}', headers={"Content-Type": "application/json"}
        ),
    )
    client._opener = opener

    assert client.get_version() == {"model": "FX9600"}

    login_request = opener.calls[0][0]
    expected_basic = base64.b64encode(b"admin:secret").decode("ascii")
    assert login_request.full_url.endswith("/cloud/localRestLogin")
    assert login_request.get_header("Authorization") == f"Basic {expected_basic}"

    version_request = opener.calls[1][0]
    assert version_request.full_url.endswith("/cloud/version")
    assert version_request.get_header("Authorization") == "Bearer synthetic-token"


def test_hostname_update_uses_documented_json_key():
    client = ZebraIoTConnector("https://reader.example", token="synthetic-token")
    opener = FakeOpener(FakeResponse())
    client._opener = opener

    assert client.set_hostname("lab-reader") is None

    request = opener.calls[0][0]
    assert request.get_method() == "PUT"
    assert request.full_url.endswith("/cloud/hostname")
    assert json.loads(request.data) == {"hostname": "lab-reader"}


def test_start_uses_documented_persistence_field():
    client = ZebraIoTConnector("https://reader.example", token="synthetic-token")
    opener = FakeOpener(FakeResponse())
    client._opener = opener

    client.start(do_not_persist_state=False)

    request = opener.calls[0][0]
    assert request.get_method() == "PUT"
    assert request.full_url.endswith("/cloud/start")
    assert json.loads(request.data) == {"doNotPersistState": False}


def test_absolute_request_url_must_stay_on_reader_origin():
    client = ZebraIoTConnector("https://reader.example", token="synthetic-token")

    with pytest.raises(ValueError, match="configured reader host"):
        client.request("GET", "https://other.example/cloud/version")
