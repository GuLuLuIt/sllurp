from pathlib import Path

path = Path("sllurp/llrp.py")
text = path.read_text()
text = text.replace("    AF_INET,\n", "", 1)
text = text.replace("    SOCK_STREAM,\n", "", 1)
text = text.replace("    socket,\n", "    create_connection,\n", 1)
old = '''            self._socket = socket(AF_INET, SOCK_STREAM)
            # Sllurp original timeout is 3s
            self._socket.settimeout(self._socktimeout)
            self._socket.connect((self._host, self._port))
'''
new = '''            self._socket = create_connection(
                (self._host, self._port), timeout=self._socktimeout
            )
            # Preserve the configured timeout after connection establishment.
            self._socket.settimeout(self._socktimeout)
'''
if old not in text:
    raise SystemExit("connection target not found")
path.write_text(text.replace(old, new, 1))

Path("tests/test_address_resolution.py").write_text(
    '''import sllurp.llrp as llrp_module
from sllurp.llrp import LLRPReaderClient


class FakeSocket:
    def __init__(self):
        self.options = []
        self.timeout = None

    def setsockopt(self, *args):
        self.options.append(args)

    def settimeout(self, value):
        self.timeout = value


def test_reader_client_uses_resolver_aware_create_connection(monkeypatch):
    calls = []
    sock = FakeSocket()

    def fake_create_connection(address, timeout):
        calls.append((address, timeout))
        return sock

    monkeypatch.setattr(llrp_module, "create_connection", fake_create_connection)
    reader = LLRPReaderClient("reader.example", 5084, timeout=2.5)
    reader._connect_socket()

    assert calls == [(("reader.example", 5084), 2.5)]
    assert reader._socket is sock
'''
)
