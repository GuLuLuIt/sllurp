import sllurp.llrp as llrp_module
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
