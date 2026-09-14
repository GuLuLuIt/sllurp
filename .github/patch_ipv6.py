from pathlib import Path

for filename in ("sllurp/llrp.py", "sllurp/secure.py"):
    path = Path(filename)
    text = path.read_text()
    text = text.replace("    AF_INET,\n    AF_INET6,\n", "", 1)
    if "    socket,\n" not in text:
        raise SystemExit(f"socket import target not found in {filename}")
    text = text.replace("    socket,\n", "    create_connection,\n", 1)

    old_socket = '''            family = AF_INET6 if ":" in self._host else AF_INET
            raw_socket = socket(family, SOCK_STREAM)
'''
    new_socket = '''            raw_socket = create_connection(
                (self._host, self._port), timeout=self._socktimeout
            )
'''
    if old_socket not in text:
        raise SystemExit(f"socket creation target not found in {filename}")
    text = text.replace(old_socket, new_socket, 1)

    old_connect = "            raw_socket.connect((self._host, self._port))\n"
    if old_connect not in text:
        raise SystemExit(f"connect target not found in {filename}")
    text = text.replace(old_connect, "", 1)
    path.write_text(text)

Path("tests/test_address_resolution.py").write_text(
    '''import sllurp.llrp as llrp_module
import sllurp.secure as secure_module
from sllurp.llrp import LLRPReaderClient
from sllurp.secure import LLRPTLSReaderClient


class FakeSocket:
    def __init__(self):
        self.options = []
        self.timeout = None
        self.closed = False

    def setsockopt(self, *args):
        self.options.append(args)

    def settimeout(self, value):
        self.timeout = value

    def close(self):
        self.closed = True


class FakeSSLContext:
    def __init__(self):
        self.wrap_calls = []

    def wrap_socket(self, sock, *, server_hostname):
        self.wrap_calls.append((sock, server_hostname))
        return sock


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


def test_secure_reader_uses_resolver_aware_create_connection(monkeypatch):
    calls = []
    sock = FakeSocket()
    context = FakeSSLContext()

    def fake_create_connection(address, timeout):
        calls.append((address, timeout))
        return sock

    monkeypatch.setattr(secure_module, "create_connection", fake_create_connection)
    reader = LLRPTLSReaderClient(
        "reader.example", 5085, timeout=3.0, ssl_context=context
    )

    reader._connect_socket()

    assert calls == [(("reader.example", 5085), 3.0)]
    assert context.wrap_calls == [(sock, "reader.example")]
    assert reader._socket is sock
'''
)
