from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# Core LLRP fixes.
path = Path("sllurp/llrp.py")
text = path.read_text()
text = replace_once(
    text,
    "LLRP_DEFAULT_PORT = 5084\nLLRP_MSG_ID_MAX = 4294967295\n",
    "LLRP_DEFAULT_PORT = 5084\nLLRP_SECURE_PORT = 5085\nLLRP_MSG_ID_MAX = 4294967295\n",
    "secure port constant",
)
text = replace_once(
    text,
    '            if (\n                self.reader_mode["MinTari"]\n                < self.config.tari\n                < self.reader_mode["MaxTari"]\n            ):\n',
    '            if (\n                self.reader_mode["MinTari"]\n                <= self.config.tari\n                <= self.reader_mode["MaxTari"]\n            ):\n',
    "inclusive Tari boundaries",
)
text = replace_once(
    text,
    "        if port is None:\n            port = LLRP_DEFAULT_PORT\n",
    "        if port is None:\n            port = (\n                LLRP_SECURE_PORT\n                if config is not None and config.tls_enabled\n                else LLRP_DEFAULT_PORT\n            )\n",
    "programmatic TLS default port",
)
text = replace_once(
    text,
    "        self.disconnect_requested = Event()\n        self._stop_main_loop = Event()\n",
    "        self.disconnect_requested = Event()\n        self._stop_main_loop = Event()\n        self._disconnected_notified = False\n",
    "disconnect notification state",
)
text = replace_once(
    text,
    '        transport = "TLS" if self.config.tls_enabled else "TCP"\n',
    '        self._disconnected_notified = False\n        transport = "TLS" if self.config.tls_enabled else "TCP"\n',
    "reset disconnect notification on connect",
)
text = replace_once(
    text,
    '        except:\n            logger.exception("Exception encountered in main loop, exiting...")\n\n        self._socket_thread = None\n',
    '        except Exception:\n            logger.exception("Exception encountered in main loop, exiting...")\n            try:\n                self.hard_disconnect()\n            except Exception:\n                logger.exception("Error while cleaning up failed reader connection")\n            self._on_disconnected()\n\n        self._socket_thread = None\n',
    "main-loop failure cleanup",
)
text = replace_once(
    text,
    "    def _on_disconnected(self):\n        for fn in self._disconnected_callbacks:\n",
    "    def _on_disconnected(self):\n        if self._disconnected_notified:\n            return\n        self._disconnected_notified = True\n        for fn in self._disconnected_callbacks:\n",
    "idempotent disconnect callback",
)
if "logger.warn(" not in text:
    raise SystemExit("deprecated logger.warn call was not found")
text = text.replace("logger.warn(", "logger.warning(")
path.write_text(text)

# Keep the legacy TLS wrapper on the same constant and cleanup behavior.
path = Path("sllurp/secure.py")
text = path.read_text()
text = replace_once(
    text,
    "from .llrp import LLRPReaderClient, SOCKET_RECV_CHUNK\n",
    "from .llrp import LLRPReaderClient, LLRP_SECURE_PORT, SOCKET_RECV_CHUNK\n",
    "shared secure port import",
)
text = replace_once(
    text,
    "\nLLRP_SECURE_PORT = 5085\n\nlogger = get_logger(__name__)\n",
    "\nlogger = get_logger(__name__)\n",
    "remove duplicate secure port constant",
)
text = replace_once(
    text,
    '        logger.info("connected securely to %s (:%s)", self._host, self._port)\n',
    '        self._disconnected_notified = False\n        logger.info("connected securely to %s (:%s)", self._host, self._port)\n',
    "secure reconnect callback reset",
)
text = replace_once(
    text,
    '        except Exception:\n            logger.exception("Exception encountered in secure main loop, exiting...")\n\n        self._socket_thread = None\n',
    '        except Exception:\n            logger.exception("Exception encountered in secure main loop, exiting...")\n            try:\n                self.hard_disconnect()\n            except Exception:\n                logger.exception("Error while cleaning up failed secure reader connection")\n            self._on_disconnected()\n\n        self._socket_thread = None\n',
    "secure main-loop failure cleanup",
)
path.write_text(text)

# Use the shared management exception for every vendor.
path = Path("sllurp/zebra_management.py")
text = path.read_text()
text = replace_once(
    text,
    "from .reader_management import HTTPReaderManager, ReaderManagementError\n",
    "from .reader_management import (\n    HTTPReaderManager,\n    ReaderManagementError,\n    UnsupportedReaderOperation,\n)\n",
    "shared unsupported-operation import",
)
text = replace_once(
    text,
    '\n\nclass UnsupportedReaderOperation(ReaderManagementError):\n    """Raised when a documented reader/model does not support an operation."""\n\n\nclass ZebraRMManager:\n',
    "\n\nclass ZebraRMManager:\n",
    "remove duplicate unsupported-operation class",
)
path.write_text(text)

# Regression tests for the core fixes.
path = Path("tests/test_regressions.py")
text = path.read_text()
text = replace_once(
    text,
    "import struct\n\nimport pytest\n",
    "import struct\nfrom unittest.mock import Mock\n\nimport pytest\n",
    "regression Mock import",
)
text = replace_once(
    text,
    "    LLRPReaderClient,\n    LLRPReaderConfig,\n",
    "    LLRPReaderClient,\n    LLRPReaderConfig,\n    LLRP_SECURE_PORT,\n",
    "regression secure port import",
)
addition = r'''

@pytest.mark.parametrize("tari", [10, 20])
def test_parse_capabilities_accepts_tari_boundaries(tari):
    config = LLRPReaderConfig(
        {
            "start_inventory": False,
            "reset_on_connect": False,
            "mode_identifier": 1,
            "tari": tari,
        }
    )
    client = LLRPClient(config, transport_tx_write=lambda _: None)
    capabilities = {
        "GeneralDeviceCapabilities": {"MaxNumberOfAntennaSupported": 1},
        "RegulatoryCapabilities": {
            "UHFBandCapabilities": {
                "TransmitPowerLevelTableEntry": [
                    {"Index": 1, "TransmitPowerValue": 3000}
                ],
                "UHFC1G2RFModeTable": {
                    "UHFC1G2RFModeTableEntry": [
                        {"ModeIdentifier": 1, "MinTari": 10, "MaxTari": 20}
                    ]
                },
            }
        },
    }

    client.parseCapabilities(capabilities)
    assert client.reader_mode["ModeIdentifier"] == 1


def test_reader_client_selects_secure_default_port_from_config():
    secure_config = LLRPReaderConfig(
        {"tls_enabled": True, "start_inventory": False, "reset_on_connect": False}
    )
    secure_reader = LLRPReaderClient("reader.example", config=secure_config)
    assert secure_reader.get_peername() == ("reader.example", LLRP_SECURE_PORT)

    explicit_reader = LLRPReaderClient(
        "reader.example", port=55085, config=secure_config
    )
    assert explicit_reader.get_peername() == ("reader.example", 55085)

    plain_reader = LLRPReaderClient("reader.example")
    assert plain_reader.get_peername() == ("reader.example", 5084)


def test_disconnect_callbacks_are_idempotent():
    reader = LLRPReaderClient("localhost")
    called = []
    reader.add_disconnected_callback(called.append)

    reader._on_disconnected()
    reader._on_disconnected()

    assert called == [reader]


def test_main_loop_unexpected_failure_cleans_up_and_notifies(monkeypatch):
    reader = LLRPReaderClient("localhost")
    reader._socket = Mock()
    called = []
    reader.add_disconnected_callback(called.append)

    def fail_select(*_args, **_kwargs):
        raise RuntimeError("select failed")

    monkeypatch.setattr("sllurp.llrp.select.select", fail_select)
    reader.main_loop()

    assert reader._socket is None
    assert called == [reader]
    reader._on_disconnected()
    assert called == [reader]
'''
if "def test_parse_capabilities_accepts_tari_boundaries" in text:
    raise SystemExit("regression tests already present")
path.write_text(text.rstrip() + addition + "\n")

# Verify Zebra exports the shared exception identity.
path = Path("tests/test_zebra_management.py")
text = path.read_text()
text = replace_once(
    text,
    "from sllurp.reader_management import ReaderManagementError\n",
    "from sllurp.reader_management import (\n    ReaderManagementError,\n    UnsupportedReaderOperation as SharedUnsupportedReaderOperation,\n)\n",
    "shared exception test import",
)
if "def test_zebra_uses_shared_unsupported_operation_exception" in text:
    raise SystemExit("shared exception regression test already present")
text = text.rstrip() + r'''


def test_zebra_uses_shared_unsupported_operation_exception():
    assert UnsupportedReaderOperation is SharedUnsupportedReaderOperation
''' + "\n"
path.write_text(text)

# Verify secure main-loop cleanup as well.
path = Path("tests/test_secure.py")
text = path.read_text()
if "def test_secure_main_loop_unexpected_failure_cleans_up" in text:
    raise SystemExit("secure cleanup regression test already present")
text = text.rstrip() + r'''


def test_secure_main_loop_unexpected_failure_cleans_up(monkeypatch):
    reader = LLRPTLSReaderClient(
        "reader.example.test",
        ssl_context=Mock(),
    )
    tls_socket = Mock()
    tls_socket.pending.return_value = 0
    reader._socket = tls_socket
    called = []
    reader.add_disconnected_callback(called.append)

    def fail_select(*_args, **_kwargs):
        raise RuntimeError("select failed")

    monkeypatch.setattr("sllurp.secure.select.select", fail_select)
    reader.main_loop()

    assert reader._socket is None
    assert called == [reader]
''' + "\n"
path.write_text(text)
