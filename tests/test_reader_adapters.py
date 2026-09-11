import json

import pytest

import sllurp.reader_adapters as adapters
from sllurp.reader_adapters import (
    ImpinjR700ReaderManager,
    LLRPOnlyReaderManager,
    ReaderIdentity,
    ReaderManagementUnsupported,
    ZebraReaderManager,
    create_reader_manager,
)
from sllurp.reader_management import ReaderHTTPResponse, ReaderManagementError


class FakeHTTP:
    instances = []
    login_body = json.dumps({"message": "JWT Token: token-123"}).encode()

    def __init__(self, base_url, **kwargs):
        self.base_url = base_url
        self.kwargs = kwargs
        self.calls = []
        FakeHTTP.instances.append(self)

    def request(
        self,
        method,
        path="",
        *,
        json_body=None,
        data=None,
        headers=None,
    ):
        self.calls.append((method, path, json_body, data, headers))
        if path == "/cloud/localRestLogin":
            return ReaderHTTPResponse(200, {}, self.login_body)
        if path == "/cloud/version":
            payload = {
                "model": "FX9600",
                "serialNumber": "SERIAL",
                "readerApplication": "3.0",
            }
        elif path == "/api/v1/status":
            payload = {
                "status": "idle",
                "serialNumber": "R7SERIAL",
                "firmwareVersion": "8.0",
            }
        else:
            payload = {"method": method, "path": path, "body": json_body}
        return ReaderHTTPResponse(
            200, {"Content-Type": "application/json"}, json.dumps(payload).encode()
        )


@pytest.fixture(autouse=True)
def fake_http(monkeypatch):
    FakeHTTP.instances = []
    FakeHTTP.login_body = json.dumps(
        {"message": "JWT Token: token-123"}
    ).encode()
    monkeypatch.setattr(adapters, "HTTPReaderManager", FakeHTTP)


def test_base_capability_error_is_explicit():
    manager = LLRPOnlyReaderManager("impinj", "Speedway R420")
    assert not manager.supports("reboot")
    with pytest.raises(ReaderManagementUnsupported, match="reboot"):
        manager.reboot()


@pytest.mark.parametrize(
    ("payload", "text", "expected"),
    [
        ({"token": "abc"}, "", "abc"),
        ({"message": "JWT Token: abc"}, "", "abc"),
        ({"access_token": "abc"}, "", "abc"),
        (None, "Bearer abc", "abc"),
        ("abc", "", "abc"),
        ({}, "", None),
    ],
)
def test_zebra_token_extraction(payload, text, expected):
    assert ZebraReaderManager._extract_token(payload, text) == expected


def test_zebra_login_switches_from_basic_to_bearer():
    manager = ZebraReaderManager(
        "https://reader", username="admin", password="secret", verify_tls=False
    )

    assert manager.get_status()["path"] == "/cloud/status"
    assert len(FakeHTTP.instances) == 3
    login, anonymous, bearer = FakeHTTP.instances
    assert login.kwargs["username"] == "admin"
    assert login.kwargs["password"] == "secret"
    assert anonymous.kwargs["bearer_token"] is None
    assert bearer.kwargs["bearer_token"] == "token-123"
    assert login.calls[0][1] == "/cloud/localRestLogin"
    assert bearer.calls[0][1] == "/cloud/status"


def test_zebra_login_requires_credentials():
    manager = ZebraReaderManager("http://reader")
    with pytest.raises(ReaderManagementError, match="requires username/password"):
        manager.login()


def test_zebra_login_requires_a_returned_token():
    FakeHTTP.login_body = b""
    manager = ZebraReaderManager(
        "http://reader", username="admin", password="secret"
    )
    with pytest.raises(ReaderManagementError, match="no bearer token"):
        manager.login()


def test_zebra_rejects_partial_credentials():
    with pytest.raises(ValueError, match="supplied together"):
        ZebraReaderManager("http://reader", username="admin")


def test_zebra_identity_and_read_operations():
    manager = ZebraReaderManager("http://reader", bearer_token="token")
    assert manager.identity() == ReaderIdentity("zebra", "FX9600", "SERIAL", "3.0")

    assert manager.get_status()["path"] == "/cloud/status"
    assert manager.get_settings()["path"] == "/cloud/config"
    assert manager.get_network()["path"] == "/cloud/network"
    assert manager.get_network("eth0")["body"] == {"interface": "eth0"}
    assert manager.get_mode()["path"] == "/cloud/mode"
    assert manager.get_mode(verbose=True)["body"] == {"verbose": True}
    assert manager.get_reader_capabilities()["path"] == "/cloud/readerCapabilities"
    assert manager.get_supported_regions()["path"] == "/cloud/supportedRegionList"
    assert manager.get_supported_standards("Canada")["body"] == {"region": "Canada"}
    assert manager.get_region()["path"] == "/cloud/region"
    assert manager.get_gpi()["path"] == "/cloud/gpi"
    assert manager.get_gpo()["path"] == "/cloud/gpo"
    assert manager.get_app_led()["path"] == "/cloud/app-led"
    assert manager.get_timezone()["path"] == "/cloud/timeZone"
    assert manager.get_ntp_server()["path"] == "/cloud/ntpServer"
    assert manager.get_logs()["path"] == "/cloud/logs"
    assert manager.get_name_and_description()["path"] == "/cloud/nameAndDescription"
    assert manager.list_apps()["path"] == "/cloud/apps"
    assert manager.list_certificates()["path"] == "/cloud/certificates"


def test_zebra_write_operations_use_documented_routes():
    manager = ZebraReaderManager("http://reader", bearer_token="token")

    assert manager.update_settings({"xml": "x"})["path"] == "/cloud/config"
    assert manager.update_network({"dhcp": True})["path"] == "/cloud/network"
    assert manager.reboot()["path"] == "/cloud/reboot"
    assert manager.set_mode({"mode": "INVENTORY"})["path"] == "/cloud/mode"
    assert manager.start_inventory()["path"] == "/cloud/start"
    started = manager.start_inventory(do_not_persist_state=True)
    assert started["body"] == {"doNotPersistState": True}
    assert manager.stop_inventory()["path"] == "/cloud/stop"
    assert manager.set_gpo(2, True)["body"] == {"port": 2, "state": True}

    led = manager.set_app_led("GREEN", 5, flash=True)
    assert led["path"].startswith("/cloud/app-led?")
    assert "color=green" in led["path"]
    assert "seconds=5" in led["path"]
    assert "flash=true" in led["path"]

    assert manager.set_timezone({"timeZone": "UTC"})["path"] == "/cloud/timeZone"
    assert manager.set_ntp_server({"server": "time.google.com"})["path"] == "/cloud/ntpServer"
    assert manager.set_logs({"radioPacketLog": True})["path"] == "/cloud/logs"
    assert manager.clear_log("syslog")["path"] == "/cloud/logs/syslog"
    assert manager.get_log("RcLog").status == 200
    renamed = manager.set_name_and_description("dock-reader", "north dock")
    assert renamed["body"] == {"name": "dock-reader", "description": "north dock"}

    assert manager.install_app({"url": "https://host/app"})["path"] == "/cloud/apps/install"
    assert manager.uninstall_app("myapp")["path"] == "/cloud/apps/myapp/uninstall"
    assert manager.start_app("myapp")["path"] == "/cloud/apps/myapp/start"
    assert manager.stop_app("myapp")["path"] == "/cloud/apps/myapp/stop"
    auto = manager.set_app_autostart("myapp", True)
    assert auto["body"] == {"autostart": True}
    passthrough = manager.app_request("myapp", "ping")
    assert passthrough["body"] == {"userapp": "myapp", "command": "ping"}

    installed = manager.install_certificate("client-ca", {"type": "client"})
    assert installed["path"] == "/cloud/certificates/client-ca"
    refreshed = manager.refresh_certificate("client-ca", "server")
    assert refreshed["body"] == {"type": "server"}
    deleted = manager.delete_certificate("client-ca", "client")
    assert deleted["path"] == "/cloud/certificates/client-ca"
    assert deleted["body"] == {"type": "client"}

    assert manager.update_firmware({"url": "https://host/fw"})["path"] == "/cloud/os"
    assert manager.revert_firmware()["path"] == "/cloud/revertbackOS"


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda m: m.get_supported_standards(""), "region"),
        (lambda m: m.set_gpo(0, True), "port"),
        (lambda m: m.set_gpo(True, True), "port"),
        (lambda m: m.set_app_led("blue", 1), "color"),
        (lambda m: m.set_app_led("green", -1), "seconds"),
        (lambda m: m.set_app_led("green", True), "seconds"),
        (lambda m: m.clear_log("../x"), "log_type"),
        (lambda m: m.set_name_and_description("", "x"), "name"),
        (lambda m: m.start_app("../x"), "appname"),
        (lambda m: m.refresh_certificate("ca", "bad"), "cert_type"),
        (lambda m: m.delete_certificate("ca", "server"), "cert_type"),
    ],
)
def test_zebra_validation(call, message):
    manager = ZebraReaderManager("http://reader", bearer_token="token")
    with pytest.raises(ValueError, match=message):
        call(manager)


def test_zebra_raw_request_is_available():
    manager = ZebraReaderManager("http://reader", bearer_token="token")
    response = manager.request(
        "POST", "/vendor/future", json_body={"x": 1}, headers={"X-Test": "1"}
    )
    assert response.json()["path"] == "/vendor/future"
    assert FakeHTTP.instances[-1].calls[-1][4] == {"X-Test": "1"}


def test_impinj_identity_and_read_operations():
    manager = ImpinjR700ReaderManager(
        "https://reader",
        model="R700",
        username="root",
        password="impinj",
        verify_tls=False,
    )

    assert manager.identity() == ReaderIdentity(
        "impinj", "R700", "R7SERIAL", "8.0"
    )
    assert manager.get_mqtt()["path"] == "/api/v1/mqtt"
    assert manager.get_profiles()["path"] == "/api/v1/profiles"
    assert (
        manager.get_inventory_presets_schema()["path"]
        == "/api/v1/profiles/inventory/presets-schema"
    )
    assert (
        manager.list_inventory_presets()["path"]
        == "/api/v1/profiles/inventory/presets"
    )
    assert (
        manager.get_inventory_preset("dock")["path"]
        == "/api/v1/profiles/inventory/presets/dock"
    )
    assert FakeHTTP.instances[-1].kwargs["username"] == "root"


def test_impinj_write_operations_and_validation():
    manager = ImpinjR700ReaderManager("http://reader", model="R720")

    assert manager.update_mqtt({"host": "broker"})["path"] == "/api/v1/mqtt"
    assert (
        manager.update_inventory_preset("dock", {"power": 30})["path"]
        == "/api/v1/profiles/inventory/presets/dock"
    )
    assert (
        manager.delete_inventory_preset("dock")["path"]
        == "/api/v1/profiles/inventory/presets/dock"
    )
    assert (
        manager.start_inventory("dock")["path"]
        == "/api/v1/profiles/inventory/presets/dock/start"
    )
    assert manager.stop_inventory()["path"] == "/api/v1/profiles/stop"

    with pytest.raises(ValueError, match="preset_id"):
        manager.get_inventory_preset("../bad")


def test_factory_selects_supported_families_and_marks_legacy_llrp_only():
    zebra = create_reader_manager(
        "Zebra", "FXR90-AA", "https://reader", bearer_token="token"
    )
    assert isinstance(zebra, ZebraReaderManager)
    assert zebra.model == "FXR90"

    impinj = create_reader_manager("Impinj", "R720", "https://reader")
    assert isinstance(impinj, ImpinjR700ReaderManager)

    legacy = create_reader_manager("Impinj", "Speedway R420")
    assert isinstance(legacy, LLRPOnlyReaderManager)
    assert legacy.vendor == "impinj"

    motorola = create_reader_manager("Motorola", "MC9190-Z")
    assert isinstance(motorola, LLRPOnlyReaderManager)


def test_factory_validates_required_fields_and_base_url():
    with pytest.raises(ValueError, match="vendor and model"):
        create_reader_manager("", "R700", "http://reader")
    with pytest.raises(ValueError, match="base_url"):
        create_reader_manager("zebra", "FX9600")
    with pytest.raises(ValueError, match="base_url"):
        create_reader_manager("impinj", "R700")
