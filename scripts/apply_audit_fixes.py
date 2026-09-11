"""Apply the first audited sllurp correctness fixes.

This is intentionally strict: every replacement must match the expected
upstream source exactly so an unexpected source change fails instead of
silently modifying the wrong code.
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


# C1G2 lock validation must validate DataField itself.
replace_exact(
    "sllurp/llrp.py",
    "if DataField < 0 or Privilege > 4:",
    "if DataField < 0 or DataField > 4:",
)

# ChannelList is the canonical key used by ROSpec generation and CLI verbs.
replace_exact(
    "sllurp/llrp.py",
    'frequencies.get("Channelist", [])',
    'frequencies.get("ChannelList", [])',
    expected=2,
)
replace_exact(
    "sllurp/llrp.py",
    '"Channelist": [DEFAULT_CHANNEL_INDEX],',
    '"ChannelList": [DEFAULT_CHANNEL_INDEX],',
)

# Preserve compatibility for callers that used the historical misspelling.
replace_exact(
    "sllurp/llrp.py",
    "    def validate_config(self):\n        if hasattr(self, \"tx_power\"):\n",
    "    def validate_config(self):\n"
    "        if \"Channelist\" in self.frequencies and \"ChannelList\" not in self.frequencies:\n"
    "            self.frequencies[\"ChannelList\"] = self.frequencies.pop(\"Channelist\")\n"
    "        if hasattr(self, \"tx_power\"):\n",
)

# Invalid Tari is documented as a configuration error; actually raise it.
replace_exact(
    "sllurp/llrp.py",
    "                errstr = (\n"
    "                    \"Requested Tari {} is incompatible with selected \"\n"
    "                    \"mode {}\".format(self.config.tari, self.reader_mode)\n"
    "                )\n\n"
    "        logger.info(\"using reader mode: %s\", self.reader_mode)\n",
    "                errstr = (\n"
    "                    \"Requested Tari {} is incompatible with selected \"\n"
    "                    \"mode {}\".format(self.config.tari, self.reader_mode)\n"
    "                )\n"
    "                raise ReaderConfigurationError(errstr)\n\n"
    "        logger.info(\"using reader mode: %s\", self.reader_mode)\n",
)

# setTxPower expects table indexes, not the dBm value stored in the table.
replace_exact(
    "sllurp/llrp.py",
    "        if tx_pow_dbm is None:\n"
    "            # select max TX power\n"
    "            ret_tx_power = {\n"
    "                ant: self.tx_power_table[-1] for ant in self.config.antennas\n"
    "            }\n",
    "        if tx_pow_dbm is None:\n"
    "            # select max TX power\n"
    "            max_power_idx = self.tx_power_table.index(max(self.tx_power_table))\n"
    "            ret_tx_power = {ant: max_power_idx for ant in self.config.antennas}\n",
)

# Clearing an unknown state must not wipe unrelated message callbacks.
replace_exact(
    "sllurp/llrp.py",
    "    def clear_state_callback(self, state):\n"
    "        if state in self._llrp_state_callbacks:\n"
    "            self._llrp_state_callbacks[state] = []\n"
    "        else:\n"
    "            self._llrp_message_callbacks = defaultdict(list)\n",
    "    def clear_state_callback(self, state):\n"
    "        if state in self._llrp_state_callbacks:\n"
    "            self._llrp_state_callbacks[state] = []\n",
)

# A new TCP stream must never inherit framing bytes from a dead connection.
replace_exact(
    "sllurp/llrp.py",
    "    def hard_disconnect(self):\n"
    "        \"\"\"Stop the recv worker, and close sockets\"\"\"\n"
    "        self._stop_main_loop.set()\n",
    "    def hard_disconnect(self):\n"
    "        \"\"\"Stop the recv worker, close sockets, and reset frame state.\"\"\"\n"
    "        self.partial_data = b\"\"\n"
    "        self.expected_bytes = 0\n"
    "        self._stop_main_loop.set()\n",
)

# Impinj decoder initializes ChannelList, so append decoded indexes there.
replace_exact(
    "sllurp/llrp_proto.py",
    '        par["ChannelListIndex"].append(\n',
    '        par["ChannelList"].append(\n',
)

# The log CLI namedtuple declares both options; forward them to the verb.
replace_exact(
    "sllurp/cli.py",
    "        epc=epc,\n"
    "        reader_timestamp=reader_timestamp,\n"
    "    )\n"
    "    logger.debug(\"log args: %s\", args)\n",
    "        epc=epc,\n"
    "        reader_timestamp=reader_timestamp,\n"
    "        frequencies=frequencies,\n"
    "        hoptable_id=hoptable_id,\n"
    "    )\n"
    "    logger.debug(\"log args: %s\", args)\n",
)

# Explicitly discover all sllurp subpackages in built wheels.
replace_exact(
    "pyproject.toml",
    "[tool.setuptools]\npackages = [\"sllurp\"]\n",
    "[tool.setuptools.packages.find]\ninclude = [\"sllurp*\"]\n",
)

print("Applied audited fixes successfully")
