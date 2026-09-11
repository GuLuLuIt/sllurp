"""Apply capability-driven Zebra FXR90 / secure LLRP support.

Every edit is guarded by an exact source match so an unexpected source change
fails the workflow instead of silently patching the wrong code.
"""

from pathlib import Path


def replace_exact(path, old, new, expected=1):
    path = Path(path)
    text = path.read_text()
    count = text.count(old)
    if count != expected:
        raise RuntimeError(
            f"{path}: expected {expected} occurrence(s), found {count}: {old!r}"
        )
    path.write_text(text.replace(old, new))


# ---------------------------------------------------------------------------
# Core transport/config: optional TLS for Zebra secure LLRP while retaining
# plain TCP as the backwards-compatible default.
# ---------------------------------------------------------------------------
replace_exact(
    "sllurp/llrp.py",
    "import select\n\nfrom binascii import hexlify\n",
    "import select\nimport ssl\n\nfrom binascii import hexlify\n",
)

replace_exact(
    "sllurp/llrp.py",
    "        self.reconnect = False\n"
    "        self.start_inventory = True\n"
    "        self.reset_on_connect = True\n\n"
    "        ## Extensions specific\n",
    "        self.reconnect = False\n"
    "        self.start_inventory = True\n"
    "        self.reset_on_connect = True\n\n"
    "        # Optional TLS transport. Zebra FXR90 readers can expose LLRP in\n"
    "        # secure mode; plain TCP remains the default for existing readers.\n"
    "        self.tls_enabled = False\n"
    "        self.tls_verify = True\n"
    "        self.tls_ca_file = None\n"
    "        self.tls_client_cert = None\n"
    "        self.tls_client_key = None\n"
    "        self.tls_server_hostname = None\n\n"
    "        ## Extensions specific\n",
)

replace_exact(
    "sllurp/llrp.py",
    "    def validate_config(self):\n"
    "        if \"Channelist\" in self.frequencies and \"ChannelList\" not in self.frequencies:\n"
    "            self.frequencies[\"ChannelList\"] = self.frequencies.pop(\"Channelist\")\n"
    "        if hasattr(self, \"tx_power\"):\n",
    "    def validate_config(self):\n"
    "        if \"Channelist\" in self.frequencies and \"ChannelList\" not in self.frequencies:\n"
    "            self.frequencies[\"ChannelList\"] = self.frequencies.pop(\"Channelist\")\n"
    "        if self.tls_client_key and not self.tls_client_cert:\n"
    "            raise LLRPError(\"tls_client_key requires tls_client_cert\")\n"
    "        if hasattr(self, \"tx_power\"):\n",
)

old_connect = '''    def _connect_socket(self):
        if self._socket:
            raise ReaderConfigurationError("Already connected")
        try:
            self._socket = socket(AF_INET, SOCK_STREAM)
            # Sllurp original timeout is 3s
            self._socket.settimeout(self._socktimeout)
            self._socket.connect((self._host, self._port))
            self._socket.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
            self._socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        except:
            self._socket = None
            raise
        logger.info("connected to %s (:%s)", self._host, self._port)
        return True
'''

new_connect = '''    def _create_tls_context(self):
        """Create the SSL context used for secure LLRP connections."""
        if self.config.tls_verify:
            context = ssl.create_default_context(cafile=self.config.tls_ca_file)
        else:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        if self.config.tls_client_cert:
            context.load_cert_chain(
                certfile=self.config.tls_client_cert,
                keyfile=self.config.tls_client_key,
            )
        return context

    def _socket_has_pending_data(self):
        """Return whether an SSL socket has already-decrypted buffered data."""
        pending = getattr(self._socket, "pending", None)
        if pending is None:
            return False
        try:
            return pending() > 0
        except (OSError, ValueError):
            return False

    def _connect_socket(self):
        if self._socket:
            raise ReaderConfigurationError("Already connected")

        raw_socket = None
        try:
            raw_socket = socket(AF_INET, SOCK_STREAM)
            # Sllurp original timeout is 3s
            raw_socket.settimeout(self._socktimeout)
            raw_socket.connect((self._host, self._port))
            raw_socket.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
            raw_socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)

            if self.config.tls_enabled:
                context = self._create_tls_context()
                server_hostname = self.config.tls_server_hostname or self._host
                self._socket = context.wrap_socket(
                    raw_socket, server_hostname=server_hostname
                )
            else:
                self._socket = raw_socket
        except:
            sock = self._socket or raw_socket
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
            self._socket = None
            raise

        transport = "TLS" if self.config.tls_enabled else "TCP"
        logger.info(
            "connected to %s (:%s) over %s", self._host, self._port, transport
        )
        return True
'''
replace_exact("sllurp/llrp.py", old_connect, new_connect)

replace_exact(
    "sllurp/llrp.py",
    "                socket_list = [self._socket]\n"
    "                # Get the list sockets which are readable\n"
    "                read_sockets, write_sockets, error_sockets = select.select(\n"
    "                    socket_list, [], []\n"
    "                )\n",
    "                socket_list = [self._socket]\n"
    "                # SSLSocket may already have decrypted application data\n"
    "                # buffered even when the underlying fd is not readable.\n"
    "                if self._socket_has_pending_data():\n"
    "                    read_sockets = socket_list\n"
    "                else:\n"
    "                    read_sockets, _, _ = select.select(socket_list, [], [])\n",
)

# ---------------------------------------------------------------------------
# CLI: expose the same TLS controls on every reader command.
# ---------------------------------------------------------------------------
tls_helper = '''logger = loggie.get_logger(__name__)


def tls_options(func):
    """Add secure-LLRP transport options to a reader command."""
    options = [
        click.option(
            "--tls",
            "tls_enabled",
            is_flag=True,
            default=False,
            help="Connect to the reader using TLS-secured LLRP.",
        ),
        click.option(
            "--tls-verify/--tls-no-verify",
            "tls_verify",
            default=True,
            help="Verify the reader TLS certificate (default: verify).",
        ),
        click.option(
            "--tls-ca-file",
            type=click.Path(),
            help="CA certificate bundle used to verify the reader.",
        ),
        click.option(
            "--tls-client-cert",
            type=click.Path(),
            help="Client certificate for mutual TLS / peer validation.",
        ),
        click.option(
            "--tls-client-key",
            type=click.Path(),
            help="Private key for --tls-client-cert.",
        ),
        click.option(
            "--tls-server-hostname",
            help="TLS SNI/certificate hostname override (useful when connecting by IP).",
        ),
    ]
    for option in reversed(options):
        func = option(func)
    return func
'''
replace_exact(
    "sllurp/cli.py",
    "logger = loggie.get_logger(__name__)\n",
    tls_helper.rstrip("\n"),
)

for command in ("inventory", "log", "access", "reset"):
    replace_exact(
        "sllurp/cli.py",
        f"def {command}(",
        f"@tls_options\ndef {command}(",
    )

# Function signatures: append TLS values after existing command-specific args.
replace_exact(
    "sllurp/cli.py",
    "    frequencies,\n    hoptable_id,\n):\n"
    "    \"\"\"Conduct inventory (searching the area around the antennas).\"\"\"\n",
    "    frequencies,\n    hoptable_id,\n"
    "    tls_enabled,\n    tls_verify,\n    tls_ca_file,\n    tls_client_cert,\n    tls_client_key,\n    tls_server_hostname,\n):\n"
    "    \"\"\"Conduct inventory (searching the area around the antennas).\"\"\"\n",
)
replace_exact(
    "sllurp/cli.py",
    "    reader_timestamp,\n    frequencies,\n    hoptable_id,\n):\n"
    "    Args = namedtuple(\n",
    "    reader_timestamp,\n    frequencies,\n    hoptable_id,\n"
    "    tls_enabled,\n    tls_verify,\n    tls_ca_file,\n    tls_client_cert,\n    tls_client_key,\n    tls_server_hostname,\n):\n"
    "    Args = namedtuple(\n",
)
replace_exact(
    "sllurp/cli.py",
    "    access_password,\n    frequencies,\n    hoptable_id,\n):\n"
    "    Args = namedtuple(\n",
    "    access_password,\n    frequencies,\n    hoptable_id,\n"
    "    tls_enabled,\n    tls_verify,\n    tls_ca_file,\n    tls_client_cert,\n    tls_client_key,\n    tls_server_hostname,\n):\n"
    "    Args = namedtuple(\n",
)
replace_exact(
    "sllurp/cli.py",
    "@tls_options\ndef reset(host, port):\n"
    "    Args = namedtuple(\"Args\", [\"host\", \"port\"])\n"
    "    args = Args(host=host, port=port)\n",
    "@tls_options\ndef reset(\n"
    "    host,\n    port,\n    tls_enabled,\n    tls_verify,\n    tls_ca_file,\n    tls_client_cert,\n    tls_client_key,\n    tls_server_hostname,\n):\n"
    "    Args = namedtuple(\n"
    "        \"Args\",\n"
    "        [\n"
    "            \"host\",\n"
    "            \"port\",\n"
    "            \"tls_enabled\",\n"
    "            \"tls_verify\",\n"
    "            \"tls_ca_file\",\n"
    "            \"tls_client_cert\",\n"
    "            \"tls_client_key\",\n"
    "            \"tls_server_hostname\",\n"
    "        ],\n"
    "    )\n"
    "    args = Args(\n"
    "        host=host,\n"
    "        port=port,\n"
    "        tls_enabled=tls_enabled,\n"
    "        tls_verify=tls_verify,\n"
    "        tls_ca_file=tls_ca_file,\n"
    "        tls_client_cert=tls_client_cert,\n"
    "        tls_client_key=tls_client_key,\n"
    "        tls_server_hostname=tls_server_hostname,\n"
    "    )\n",
)

# Add TLS fields to the first three namedtuple declarations. The target string
# is shared exactly three times (inventory/log/access).
replace_exact(
    "sllurp/cli.py",
    '            "hoptable_id",\n        ],\n',
    '            "hoptable_id",\n'
    '            "tls_enabled",\n'
    '            "tls_verify",\n'
    '            "tls_ca_file",\n'
    '            "tls_client_cert",\n'
    '            "tls_client_key",\n'
    '            "tls_server_hostname",\n'
    '        ],\n',
    expected=3,
)

# Add TLS keyword values to Args construction for inventory/log/access.
replace_exact(
    "sllurp/cli.py",
    "        frequencies=frequencies,\n"
    "        hoptable_id=hoptable_id,\n"
    "    )\n",
    "        frequencies=frequencies,\n"
    "        hoptable_id=hoptable_id,\n"
    "        tls_enabled=tls_enabled,\n"
    "        tls_verify=tls_verify,\n"
    "        tls_ca_file=tls_ca_file,\n"
    "        tls_client_cert=tls_client_cert,\n"
    "        tls_client_key=tls_client_key,\n"
    "        tls_server_hostname=tls_server_hostname,\n"
    "    )\n",
    expected=3,
)

# ---------------------------------------------------------------------------
# Verb layers: pass transport settings into LLRPReaderConfig.
# ---------------------------------------------------------------------------
tls_factory = (
    "        tls_enabled=args.tls_enabled,\n"
    "        tls_verify=args.tls_verify,\n"
    "        tls_ca_file=args.tls_ca_file,\n"
    "        tls_client_cert=args.tls_client_cert,\n"
    "        tls_client_key=args.tls_client_key,\n"
    "        tls_server_hostname=args.tls_server_hostname,\n"
)

replace_exact(
    "sllurp/verb/inventory.py",
    "        keepalive_interval=args.keepalive_interval,\n"
    "        impinj_extended_configuration=args.impinj_extended_configuration,\n",
    "        keepalive_interval=args.keepalive_interval,\n"
    + tls_factory
    + "        impinj_extended_configuration=args.impinj_extended_configuration,\n",
)
replace_exact(
    "sllurp/verb/log.py",
    "        tx_power=args.tx_power,\n"
    "        start_inventory=True,\n",
    "        tx_power=args.tx_power,\n" + tls_factory + "        start_inventory=True,\n",
)
replace_exact(
    "sllurp/verb/access.py",
    "        tag_population=args.population,\n"
    "        start_inventory=True,\n",
    "        tag_population=args.population,\n" + tls_factory + "        start_inventory=True,\n",
)
replace_exact(
    "sllurp/verb/reset.py",
    "    factory_args = {\n"
    "        \"start_inventory\": False,\n"
    "        \"reset_on_connect\": False,\n"
    "    }\n",
    "    factory_args = {\n"
    "        \"start_inventory\": False,\n"
    "        \"reset_on_connect\": False,\n"
    "        \"tls_enabled\": args.tls_enabled,\n"
    "        \"tls_verify\": args.tls_verify,\n"
    "        \"tls_ca_file\": args.tls_ca_file,\n"
    "        \"tls_client_cert\": args.tls_client_cert,\n"
    "        \"tls_client_key\": args.tls_client_key,\n"
    "        \"tls_server_hostname\": args.tls_server_hostname,\n"
    "    }\n",
)

# ---------------------------------------------------------------------------
# Documentation: state support precisely and show safe secure-LLRP usage.
# ---------------------------------------------------------------------------
replace_exact(
    "README.rst",
    "- Zebra Fixed RFID Reader (FX7500, FX9600)\n",
    "- Zebra Fixed RFID Reader (FX7500, FX9600, FXR90 family)\n",
)

fxr90_docs = '''
Zebra FXR90
-----------

The FXR90 family can be used through its LLRP interface.  sllurp keeps antenna
handling capability-driven rather than hard-coding a particular FXR90 SKU, so
the same code works with the 4-port, integrated-antenna plus external-port, and
8-port variants.  Use antenna ``0`` to request all antennas exposed by the
reader::

    $ sllurp inventory -a 0 fxr90.example

For readers configured for secure LLRP, enable TLS.  The default is to verify
the reader certificate using the operating system trust store; a private CA
bundle can be supplied explicitly::

    $ sllurp inventory --tls --tls-ca-file /path/to/reader-ca.pem -a 0 fxr90.example

If the reader requires client-certificate authentication, also provide a
certificate and its private key::

    $ sllurp inventory --tls --tls-client-cert client.pem --tls-client-key client.key fxr90.example

When connecting to an IP address while the certificate is issued to a DNS
name, use ``--tls-server-hostname`` to set the TLS SNI/certificate hostname.
``--tls-no-verify`` is available for controlled test environments, but disables
certificate validation and should not be used as the normal production setup.

The FXR90 support here targets standard LLRP plus Zebra's secure transport.  It
does not attempt to emulate Zebra's separate IoT Connector protocol.

'''
replace_exact(
    "README.rst",
    "Reader API\n----------\n",
    fxr90_docs + "Reader API\n----------\n",
)

print("Applied FXR90 / secure LLRP support successfully")
