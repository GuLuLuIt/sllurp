from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text()


def write(path, text):
    (ROOT / path).write_text(text)


def replace(path, old, new, count=1):
    text = read(path)
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f"{path}: expected {count} occurrences, found {actual}: {old[:80]!r}")
    write(path, text.replace(old, new, count))


def regex_replace(path, pattern, repl, count=0):
    text = read(path)
    new_text, actual = re.subn(pattern, repl, text, count=count, flags=re.MULTILINE)
    if actual == 0:
        raise RuntimeError(f"{path}: pattern not found: {pattern}")
    write(path, new_text)
    return actual


# --- Core LLRP transport/state hardening ---------------------------------
replace(
    "sllurp/llrp.py",
    "    AF_INET,\n    SOCK_STREAM,",
    "    AF_INET,\n    AF_INET6,\n    SOCK_STREAM,",
)
replace(
    "sllurp/llrp.py",
    "from threading import Thread, Event",
    "from threading import Thread, Event, Timer",
)
replace(
    "sllurp/llrp.py",
    "SOCKET_RECV_CHUNK = 64 * 1024\nZEBRA_TIMED_DEDUP_MAX_SECONDS = 600",
    "SOCKET_RECV_CHUNK = 64 * 1024\nDEFAULT_MAX_MESSAGE_SIZE = 16 * 1024 * 1024\nZEBRA_TIMED_DEDUP_MAX_SECONDS = 600",
)
replace(
    "sllurp/llrp.py",
    '''        msgtype, vendorid, subtype, ver, hdr_len, full_length, msgid = (\n            msg_header_decode(data)\n        )\n''',
    '''        try:\n            msgtype, vendorid, subtype, ver, hdr_len, full_length, msgid = (\n                msg_header_decode(data)\n            )\n        except ValueError as exc:\n            raise LLRPError(f"Invalid LLRP message header: {exc}") from exc\n        if full_length < hdr_len:\n            raise LLRPError(\n                f"Invalid LLRP message length {full_length}; header is {hdr_len} bytes"\n            )\n        if full_length > len(data):\n            raise LLRPError(\n                f"Truncated LLRP message: declared {full_length} bytes, got {len(data)}"\n            )\n''',
)
replace(
    "sllurp/llrp.py",
    '''        if (\n            config.impinj_search_mode\n            or config.impinj_tag_content_selector\n            or config.impinj_extended_configuration\n            or config.impinj_event_selector\n            or config.frequencies.get("Automatic", False)\n            or len(config.frequencies.get("ChannelList", [])) > 1\n        ):\n            logger.info("Enabling Impinj extensions")\n''',
    '''        if self._uses_impinj_extensions():\n            logger.info("Enabling Impinj extensions")\n''',
)
replace(
    "sllurp/llrp.py",
    '''    def update_config(self, new_config):\n        """Update LLRPClient's config\n\n        Not completely safe, to be used with caution.\n        """\n        self.config = new_config\n\n    def setState(self, newstate, onCompletion=None):\n''',
    '''    def update_config(self, new_config):\n        """Update LLRPClient's config\n\n        Not completely safe, to be used with caution.\n        """\n        self.config = new_config\n\n    def _uses_impinj_extensions(self):\n        """Return whether the current configuration explicitly needs Impinj extensions."""\n        return bool(\n            self.config.impinj_search_mode\n            or self.config.impinj_tag_content_selector\n            or self.config.impinj_extended_configuration\n            or self.config.impinj_event_selector\n            or self.config.impinj_fixed_frequency\n        )\n\n    def setState(self, newstate, onCompletion=None):\n''',
)
replace(
    "sllurp/llrp.py",
    '''            if (\n                self.config.impinj_search_mode\n                or self.config.impinj_tag_content_selector\n                or self.config.impinj_extended_configuration\n                or self.config.impinj_event_selector\n                or self.config.frequencies.get("Automatic", False)\n                or len(self.config.frequencies.get("ChannelList", [])) > 1\n            ):\n''',
    '''            if self._uses_impinj_extensions():\n''',
)
replace(
    "sllurp/llrp.py",
    '''            frequencies=config.frequencies,\n        )\n''',
    '''            frequencies=config.frequencies,\n            impinj_fixed_frequency=config.impinj_fixed_frequency,\n        )\n''',
)
replace(
    "sllurp/llrp.py",
    '''        self.socket_receive_buffer_bytes = 1 << 20\n        self.antennas = [1]\n''',
    '''        self.socket_receive_buffer_bytes = 1 << 20\n        self.max_message_size = DEFAULT_MAX_MESSAGE_SIZE\n        self.antennas = [1]\n''',
)
replace(
    "sllurp/llrp.py",
    '''        self.tx_power_dbm = None\n        self.disconnect_when_done = self.duration and self.duration > 0\n''',
    '''        self.tx_power_dbm = None\n        self.disconnect_when_done = False\n''',
)
replace(
    "sllurp/llrp.py",
    '''        self.impinj_extended_configuration = False\n        self.impinj_search_mode = None\n''',
    '''        self.impinj_extended_configuration = False\n        self.impinj_fixed_frequency = False\n        self.impinj_search_mode = None\n''',
)
replace(
    "sllurp/llrp.py",
    '''        self.reconnect_retries = 5\n''',
    '''        self.reconnect_retries = 5\n        self.reconnect_delay = 60.0\n''',
)
replace(
    "sllurp/llrp.py",
    '''        if config_dict:\n            self.update_config(config_dict)\n\n        self.validate_config()\n''',
    '''        if config_dict:\n            self.update_config(config_dict)\n            if "disconnect_when_done" not in config_dict:\n                self.disconnect_when_done = bool(self.duration and self.duration > 0)\n\n        self.validate_config()\n''',
)
replace(
    "sllurp/llrp.py",
    '''    def validate_config(self):\n        if self.dedup_seconds is not None:\n''',
    '''    def validate_config(self):\n        if not isinstance(self.antennas, (list, tuple)) or not self.antennas:\n            raise LLRPError("antennas must be a non-empty list or tuple")\n        if any(isinstance(ant, bool) or not isinstance(ant, int) or ant < 0 for ant in self.antennas):\n            raise LLRPError("antennas must contain non-negative integers")\n        if 0 in self.antennas and len(self.antennas) != 1:\n            raise LLRPError("antenna 0 means all antennas and cannot be combined with others")\n        if (\n            isinstance(self.reconnect_retries, bool)\n            or not isinstance(self.reconnect_retries, int)\n            or self.reconnect_retries < -1\n        ):\n            raise LLRPError("reconnect_retries must be -1 or a non-negative integer")\n        if (\n            isinstance(self.reconnect_delay, bool)\n            or not isinstance(self.reconnect_delay, (int, float))\n            or self.reconnect_delay < 0\n        ):\n            raise LLRPError("reconnect_delay must be a non-negative number")\n        if (\n            self.max_message_size is not None\n            and (\n                isinstance(self.max_message_size, bool)\n                or not isinstance(self.max_message_size, int)\n                or self.max_message_size < msg_header_len\n            )\n        ):\n            raise LLRPError(\n                f"max_message_size must be at least {msg_header_len} bytes or None"\n            )\n        channel_list = self.frequencies.get("ChannelList", [])\n        if not isinstance(channel_list, (list, tuple)) or not channel_list:\n            raise LLRPError("frequencies ChannelList must contain at least one channel")\n        if any(\n            isinstance(channel, bool) or not isinstance(channel, int) or channel <= 0\n            for channel in channel_list\n        ):\n            raise LLRPError("frequency channel indexes must be positive integers")\n        if (self.frequencies.get("Automatic", False) or len(channel_list) > 1) and not self.impinj_fixed_frequency:\n            raise LLRPError(\n                "automatic or multiple frequency selection requires "\n                "impinj_fixed_frequency=True because it uses an Impinj vendor extension"\n            )\n\n        if self.dedup_seconds is not None:\n''',
)
replace(
    "sllurp/llrp.py",
    '''        if hasattr(self, "tx_power_dbm") and self.tx_power_dbm is not None:\n            if isinstance(self.tx_power_dbm, float):\n                self.tx_power_dbm = {ant: self.tx_power_dbm for ant in self.antennas}\n            elif isinstance(self.tx_power_dbm, dict):\n                if set(self.antennas) != set(self.tx_power_dbm.keys()):\n                    raise LLRPError("Must specify tx_power for each antenna")\n            else:\n                raise LLRPError("tx_power must be dict or float")\n''',
    '''        if hasattr(self, "tx_power_dbm") and self.tx_power_dbm is not None:\n            if (\n                isinstance(self.tx_power_dbm, (int, float))\n                and not isinstance(self.tx_power_dbm, bool)\n            ):\n                value = float(self.tx_power_dbm)\n                self.tx_power_dbm = {ant: value for ant in self.antennas}\n            elif isinstance(self.tx_power_dbm, dict):\n                if set(self.antennas) != set(self.tx_power_dbm.keys()):\n                    raise LLRPError("Must specify tx_power for each antenna")\n                if any(\n                    isinstance(value, bool) or not isinstance(value, (int, float))\n                    for value in self.tx_power_dbm.values()\n                ):\n                    raise LLRPError("tx_power_dbm values must be numeric")\n                self.tx_power_dbm = {\n                    ant: float(value) for ant, value in self.tx_power_dbm.items()\n                }\n            else:\n                raise LLRPError("tx_power_dbm must be a number or dict")\n''',
)
replace(
    "sllurp/llrp.py",
    '''        self._stop_main_loop = Event()\n        self._disconnected_notified = False\n\n        # for partial data transfers\n''',
    '''        self._stop_main_loop = Event()\n        self._disconnected_notified = False\n        self._duration_timer = None\n\n        # for partial data transfers\n''',
)
replace(
    "sllurp/llrp.py",
    '''            raw_socket = socket(AF_INET, SOCK_STREAM)\n''',
    '''            family = AF_INET6 if ":" in self._host else AF_INET\n            raw_socket = socket(family, SOCK_STREAM)\n''',
)
replace(
    "sllurp/llrp.py",
    '''    def connect(self, start_main_loop=True):\n        if self._socket_thread:\n            raise ReaderConfigurationError("Already connected")\n        self.disconnect_requested.clear()\n\n        self._connect_socket()\n\n        if not start_main_loop:\n            return\n''',
    '''    def _reset_protocol_session(self):\n        """Discard request callbacks and frame state from a previous transport session."""\n        self.partial_data = b""\n        self.expected_bytes = 0\n        if self.llrp:\n            self.llrp._deferreds.clear()\n            self.llrp.rospec = None\n            self.llrp.disconnecting = False\n            self.llrp.setState(LLRPReaderState.STATE_DISCONNECTED)\n\n    def _retry_connect(self):\n        remaining_attempts = self.config.reconnect_retries\n        last_error = None\n        while remaining_attempts != 0 and not self.disconnect_requested.is_set():\n            try:\n                self._connect_socket()\n                return True\n            except Exception as exc:\n                last_error = exc\n                logger.warning("Reconnection attempt failed: %s", exc)\n            if remaining_attempts > 0:\n                remaining_attempts -= 1\n            if remaining_attempts == 0:\n                break\n            if self.disconnect_requested.wait(self.config.reconnect_delay):\n                break\n        if last_error is not None:\n            raise last_error\n        return False\n\n    def connect(self, start_main_loop=True):\n        if self._socket_thread:\n            raise ReaderConfigurationError("Already connected")\n        self.disconnect_requested.clear()\n        self._reset_protocol_session()\n\n        try:\n            self._connect_socket()\n        except Exception:\n            if not self.config.reconnect:\n                raise\n            logger.warning("Initial connection failed; applying reconnect policy")\n            try:\n                self._retry_connect()\n            except Exception:\n                self._on_disconnected()\n                raise\n\n        if not start_main_loop:\n            return\n''',
)
replace(
    "sllurp/llrp.py",
    '''    def hard_disconnect(self):\n        """Stop the recv worker, close sockets, and reset frame state."""\n        self.partial_data = b""\n''',
    '''    def hard_disconnect(self):\n        """Stop the recv worker, close sockets, and reset frame state."""\n        self._cancel_duration_timer()\n        self.partial_data = b""\n''',
)
replace(
    "sllurp/llrp.py",
    '''        remaining_attempts = self.config.reconnect_retries\n        retry_delay = 60  # seconds\n\n        logger.info("Lost connection detected")\n''',
    '''        logger.info("Lost connection detected")\n''',
)
replace(
    "sllurp/llrp.py",
    '''        if not self.config.reconnect:\n            self._on_disconnected()\n            return True\n\n        while remaining_attempts:\n            try:\n                self._connect_socket()\n                return False\n            except:\n                logger.warning("Reconnection attempt failed.")\n            if remaining_attempts > 0:\n                remaining_attempts -= 1\n            if remaining_attempts == 0:\n                logger.info("Too many retries. Giving up...")\n                break\n            logger.info("Next connection attempt in %ds", retry_delay)\n            user_disconnected = self.disconnect_requested.wait(retry_delay)\n            if user_disconnected:\n                # Disconnection was requested by user\n                break\n        self._on_disconnected()\n        return True\n''',
    '''        self._reset_protocol_session()\n        if not self.config.reconnect:\n            self._on_disconnected()\n            return True\n\n        try:\n            if self._retry_connect():\n                return False\n        except Exception:\n            logger.info("Too many retries. Giving up...")\n        self._on_disconnected()\n        return True\n''',
)
replace(
    "sllurp/llrp.py",
    '''            logger.debugfast("expect %d bytes (have %d)", msg_len, data_len)\n\n            if data_len < msg_len:\n''',
    '''            logger.debugfast("expect %d bytes (have %d)", msg_len, data_len)\n            if msg_len < msg_header_len:\n                raise LLRPError(\n                    f"Invalid LLRP message length {msg_len}; minimum is {msg_header_len}"\n                )\n            if (\n                self.config.max_message_size is not None\n                and msg_len > self.config.max_message_size\n            ):\n                raise LLRPError(\n                    f"LLRP message length {msg_len} exceeds configured maximum "\n                    f"{self.config.max_message_size}"\n                )\n\n            if data_len < msg_len:\n''',
)
replace(
    "sllurp/llrp.py",
    '''                except LLRPError:\n                    logger.exception(\n                        "Failed to decode LLRPMessage; "\n                        "will not decode %d remaining bytes",\n                        data_len,\n                    )\n                    break\n''',
    '''                except LLRPError:\n                    logger.exception(\n                        "Failed to decode LLRPMessage; disconnecting to avoid frame desynchronization"\n                    )\n                    raise\n''',
)
replace(
    "sllurp/llrp.py",
    '''    def _on_disconnected(self):\n        if self._disconnected_notified:\n''',
    '''    def _cancel_duration_timer(self):\n        timer = self._duration_timer\n        self._duration_timer = None\n        if timer is not None:\n            timer.cancel()\n\n    def _duration_expired(self):\n        self._duration_timer = None\n        if self._socket is not None and not self.disconnect_requested.is_set():\n            logger.info("inventory duration elapsed; disconnecting")\n            self.disconnect()\n\n    def _schedule_duration_disconnect(self):\n        self._cancel_duration_timer()\n        if not self.config.disconnect_when_done:\n            return\n        duration = self.config.duration\n        if duration is None or duration <= 0:\n            return\n        timer = Timer(duration, self._duration_expired)\n        timer.daemon = True\n        self._duration_timer = timer\n        timer.start()\n\n    def _on_disconnected(self):\n        self._cancel_duration_timer()\n        if self._disconnected_notified:\n''',
)
replace(
    "sllurp/llrp.py",
    '''    def _on_llrp_state_changed(self, newstate):\n        """Call user callbacks if needed"""\n        for fn in self._llrp_state_callbacks[newstate]:\n''',
    '''    def _on_llrp_state_changed(self, newstate):\n        """Call user callbacks if needed"""\n        if newstate == LLRPReaderState.STATE_INVENTORYING:\n            self._schedule_duration_disconnect()\n        elif newstate == LLRPReaderState.STATE_DISCONNECTED:\n            self._cancel_duration_timer()\n        for fn in self._llrp_state_callbacks[newstate]:\n''',
)
replace(
    "sllurp/llrp.py",
    '''    def add_tag_report_callback(self, cb):\n        if not self._llrp_message_callbacks["RO_ACCESS_REPORT"]:\n            self._llrp_message_callbacks["RO_ACCESS_REPORT"].append(\n                self._on_llrp_tag_report\n            )\n\n        if cb not in self._tag_report_callbacks:\n''',
    '''    def add_tag_report_callback(self, cb):\n        callbacks = self._llrp_message_callbacks["RO_ACCESS_REPORT"]\n        if self._on_llrp_tag_report not in callbacks:\n            callbacks.append(self._on_llrp_tag_report)\n\n        if cb not in self._tag_report_callbacks:\n''',
)
replace(
    "sllurp/llrp.py",
    '''    def clear_tag_report_callback(self, cb):\n        self._tag_report_callbacks = []\n\n    def add_event_callback(self, cb):\n        if not self._llrp_message_callbacks["READER_EVENT_NOTIFICATION"]:\n            self._llrp_message_callbacks["READER_EVENT_NOTIFICATION"].append(\n                self._on_llrp_event_notification\n            )\n\n        if cb not in self._event_notification_callbacks:\n''',
    '''    def clear_tag_report_callback(self, cb=None):\n        self._tag_report_callbacks = []\n\n    def add_event_callback(self, cb):\n        callbacks = self._llrp_message_callbacks["READER_EVENT_NOTIFICATION"]\n        if self._on_llrp_event_notification not in callbacks:\n            callbacks.append(self._on_llrp_event_notification)\n\n        if cb not in self._event_notification_callbacks:\n''',
)
replace(
    "sllurp/llrp.py",
    '''    def clear_event_callback(self, cb):\n        self._event_notification_callbacks = []\n''',
    '''    def clear_event_callback(self, cb=None):\n        self._event_notification_callbacks = []\n''',
)
replace(
    "sllurp/llrp.py",
    '''    def clear_disconnected_callback(self, cb):\n        self._disconnected_callbacks = []\n''',
    '''    def clear_disconnected_callback(self, cb=None):\n        self._disconnected_callbacks = []\n''',
)
# Reject a second request expecting the same response before it can be sent.
replace(
    "sllurp/llrp.py",
    '''        sent_ids = []\n        for name in msg_dict:\n            if self.last_msg_id < LLRP_MSG_ID_MAX:\n''',
    '''        sent_ids = []\n        for name in msg_dict:\n            response_name = (\n                "IMPINJ_ENABLE_EXTENSIONS_RESPONSE"\n                if name == "IMPINJ_ENABLE_EXTENSIONS"\n                else f"{name}_RESPONSE"\n            )\n            if self._deferreds.get(response_name):\n                raise ReaderConfigurationError(\n                    f"cannot send {name}: {response_name} is already pending"\n                )\n            if self.last_msg_id < LLRP_MSG_ID_MAX:\n''',
)

# --- Decoder bounds -------------------------------------------------------
replace(
    "sllurp/llrp_decoder.py",
    '''def msg_header_decode(data):\n    msgtype, length, msgid = msg_header_unpack(data[:msg_header_size])\n''',
    '''def msg_header_decode(data):\n    if len(data) < msg_header_size:\n        raise ValueError(\n            f"truncated LLRP message header: need {msg_header_size} bytes, got {len(data)}"\n        )\n    try:\n        msgtype, length, msgid = msg_header_unpack(data[:msg_header_size])\n    except StructError as exc:\n        raise ValueError("invalid LLRP message header") from exc\n''',
)
replace(
    "sllurp/llrp_decoder.py",
    '''    if msgtype == TYPE_CUSTOM:\n        vendorid, subtype = msg_vendor_subtype_unpack(\n            data[hdr_len : hdr_len + msg_vendor_subtype_size]\n        )\n        hdr_len += msg_vendor_subtype_size\n    else:\n''',
    '''    if msgtype == TYPE_CUSTOM:\n        custom_size = hdr_len + msg_vendor_subtype_size\n        if len(data) < custom_size:\n            raise ValueError(\n                f"truncated custom LLRP header: need {custom_size} bytes, got {len(data)}"\n            )\n        try:\n            vendorid, subtype = msg_vendor_subtype_unpack(\n                data[hdr_len:custom_size]\n            )\n        except StructError as exc:\n            raise ValueError("invalid custom LLRP message header") from exc\n        hdr_len = custom_size\n    else:\n''',
)
replace(
    "sllurp/llrp_decoder.py",
    '''        vendorid = 0\n        subtype = 0\n    return msgtype, vendorid, subtype, version, hdr_len, length, msgid\n''',
    '''        vendorid = 0\n        subtype = 0\n    if length < hdr_len:\n        raise ValueError(\n            f"declared LLRP message length {length} is shorter than header {hdr_len}"\n        )\n    return msgtype, vendorid, subtype, version, hdr_len, length, msgid\n''',
)
replace(
    "sllurp/llrp_decoder.py",
    '''    partype, length = tlv_par_header_unpack(data[:tlv_par_header_size])\n    hdr_len = tlv_par_header_size\n''',
    '''    partype, length = tlv_par_header_unpack(data[:tlv_par_header_size])\n    hdr_len = tlv_par_header_size\n    if length < hdr_len:\n        raise ValueError(\n            f"declared TLV parameter length {length} is shorter than header {hdr_len}"\n        )\n''',
)
replace(
    "sllurp/llrp_decoder.py",
    '''    vendorid, subtype = par_vendor_subtype_unpack(\n        data[hdr_len : hdr_len + par_vendor_subtype_size]\n    )\n    hdr_len = custom_header_size\n''',
    '''    if length < custom_header_size:\n        raise ValueError(\n            f"declared custom parameter length {length} is shorter than header {custom_header_size}"\n        )\n    vendorid, subtype = par_vendor_subtype_unpack(\n        data[hdr_len : hdr_len + par_vendor_subtype_size]\n    )\n    hdr_len = custom_header_size\n''',
)

replace(
    "sllurp/llrp_proto.py",
    '''    partype, vendorid, subtype, hdr_len, full_length = param_header_decode(data)\n\n    if not partype:\n''',
    '''    try:\n        partype, vendorid, subtype, hdr_len, full_length = param_header_decode(data)\n    except ValueError as exc:\n        raise LLRPError(f"Invalid LLRP parameter header: {exc}") from exc\n\n    if not partype:\n''',
)
replace(
    "sllurp/llrp_proto.py",
    '''    pardata = data[hdr_len:full_length]\n\n    param_name = Param_Type2Name.get((partype, vendorid, subtype))\n''',
    '''    if full_length < hdr_len:\n        raise LLRPError(\n            f"Invalid LLRP parameter length {full_length}; header is {hdr_len} bytes"\n        )\n    if full_length > len(data):\n        raise LLRPError(\n            f"Truncated LLRP parameter: declared {full_length} bytes, got {len(data)}"\n        )\n    pardata = data[hdr_len:full_length]\n\n    param_name = Param_Type2Name.get((partype, vendorid, subtype))\n''',
)
replace(
    "sllurp/llrp_proto.py",
    '''        except KeyError:\n            logger.debugfast('\"decode\" func is missing for parameter %s', param_name)\n            decoder_error = "DecodeFunctionMissing"\n''',
    '''        except KeyError:\n            logger.debugfast('\"decode\" func is missing for parameter %s', param_name)\n            decoder_error = "DecodeFunctionMissing"\n        except (struct.error, ValueError, TypeError, IndexError) as exc:\n            raise LLRPError(f"Unable to decode parameter {param_name}: {exc}") from exc\n''',
)
# MaxTari is inclusive, and vendor fixed-frequency use is explicit from core config.
replace(
    "sllurp/llrp_proto.py",
    '''        impinj_search_mode=None,\n        impinj_tag_content_selector=None,\n        frequencies=None,\n    ):\n''',
    '''        impinj_search_mode=None,\n        impinj_tag_content_selector=None,\n        frequencies=None,\n        impinj_fixed_frequency=None,\n    ):\n''',
)
replace(
    "sllurp/llrp_proto.py",
    '''        if reader_mode is not None:\n            if tari is not None and tari < reader_mode["MaxTari"]:\n                override_tari = tari\n''',
    '''        if reader_mode is not None:\n            if (\n                tari is not None\n                and reader_mode["MinTari"] <= tari <= reader_mode["MaxTari"]\n            ):\n                override_tari = tari\n''',
)
replace(
    "sllurp/llrp_proto.py",
    '''            if frequencies.get("Automatic", False):\n                antconf["C1G2InventoryCommand"][0]["ImpinjFixedFrequencyList"] = {\n                    "FixedFrequencyMode": 1,\n                    "ChannelList": [],\n                }\n            elif len(freq_channel_list) > 1:\n                antconf["C1G2InventoryCommand"][0]["ImpinjFixedFrequencyList"] = {\n                    "FixedFrequencyMode": 2,\n                    "ChannelList": freq_channel_list,\n                }\n''',
    '''            use_impinj_fixed_frequency = impinj_fixed_frequency\n            if use_impinj_fixed_frequency is None:\n                # Preserve the direct LLRPROSpec API's historical behavior.\n                # LLRPReaderConfig passes an explicit boolean so generic readers\n                # never receive an Impinj custom parameter by accident.\n                use_impinj_fixed_frequency = (\n                    frequencies.get("Automatic", False) or len(freq_channel_list) > 1\n                )\n            if use_impinj_fixed_frequency and frequencies.get("Automatic", False):\n                antconf["C1G2InventoryCommand"][0]["ImpinjFixedFrequencyList"] = {\n                    "FixedFrequencyMode": 1,\n                    "ChannelList": [],\n                }\n            elif use_impinj_fixed_frequency and len(freq_channel_list) > 1:\n                antconf["C1G2InventoryCommand"][0]["ImpinjFixedFrequencyList"] = {\n                    "FixedFrequencyMode": 2,\n                    "ChannelList": freq_channel_list,\n                }\n''',
)

# --- Shared host:port parser / IPv6 --------------------------------------
replace(
    "sllurp/util.py",
    '''def find_closest(table, target):\n''',
    '''def split_host_port(value, default_port):\n    """Split CLI reader address syntax while preserving IPv6 literals.\n\n    IPv6 with an explicit port must use bracket notation, e.g.\n    ``[2001:db8::1]:5084``. An unbracketed IPv6 literal is treated as a host\n    with ``default_port``.\n    """\n    if value.startswith("["):\n        end = value.find("]")\n        if end < 0:\n            raise ValueError("missing closing bracket in IPv6 reader address")\n        host = value[1:end]\n        remainder = value[end + 1 :]\n        if not remainder:\n            return host, default_port\n        if not remainder.startswith(":") or not remainder[1:]:\n            raise ValueError("invalid bracketed reader address")\n        return host, int(remainder[1:])\n    if value.count(":") == 1:\n        host, port = value.rsplit(":", 1)\n        if host and port:\n            return host, int(port)\n    return value, default_port\n\n\ndef find_closest(table, target):\n''',
)

for path in ["sllurp/verb/inventory.py", "sllurp/verb/log.py", "sllurp/verb/access.py", "sllurp/verb/reset.py"]:
    text = read(path)
    if "split_host_port" not in text:
        if "from sllurp.util import monotonic" in text:
            text = text.replace(
                "from sllurp.util import monotonic",
                "from sllurp.util import monotonic, split_host_port",
                1,
            )
        elif "from sllurp.llrp import" in text:
            text = text.replace(
                "from sllurp.llrp import",
                "from sllurp.util import split_host_port\nfrom sllurp.llrp import",
                1,
            )
    old = '''    for host in args.host:\n        if ":" in host:\n            host, port = host.split(":", 1)\n            port = int(port)\n        else:\n            port = args.port\n'''
    if old not in text:
        raise RuntimeError(f"{path}: host parsing block not found")
    text = text.replace(
        old,
        '''    for host_value in args.host:\n        host, port = split_host_port(host_value, args.port)\n''',
        1,
    )
    write(path, text)

# Standalone lock utility gets the same safe parser.
replace(
    "sllurp/lock.py",
    "from sllurp.util import monotonic",
    "from sllurp.util import monotonic, split_host_port",
)
replace(
    "sllurp/lock.py",
    '''    for host in args.host:\n        if ":" in host:\n            host, port = host.split(":", 1)\n            port = int(port)\n        else:\n            port = args.port\n''',
    '''    for host_value in args.host:\n        host, port = split_host_port(host_value, args.port)\n''',
)

# Legacy secure convenience client: IPv6 literal support too.
replace(
    "sllurp/secure.py",
    "    AF_INET,\n    SOCK_STREAM,",
    "    AF_INET,\n    AF_INET6,\n    SOCK_STREAM,",
)
replace(
    "sllurp/secure.py",
    "            raw_socket = socket(AF_INET, SOCK_STREAM)",
    "            family = AF_INET6 if \":\" in self._host else AF_INET\n            raw_socket = socket(family, SOCK_STREAM)",
)

# --- CLI/vendor-frequency safety -----------------------------------------
# Add explicit vendor-extension option to inventory, log, and access.
for command_name in ["inventory", "log", "access"]:
    pass

# Inventory decorator/signature/Args/config.
replace(
    "sllurp/cli.py",
    '''@click.option(\n    "-f",\n    "--frequencies",\n    type=str,\n    default="1",\n    help="comma-separated list of frequency indexes to use (0=all;"\n    " default 1). Region and reader dependent",\n)\n@click.option(\n    "--hoptable-id",\n''',
    '''@click.option(\n    "-f",\n    "--frequencies",\n    type=str,\n    default="1",\n    help="comma-separated list of frequency indexes to use (0=all; default 1)",\n)\n@click.option(\n    "--impinj-fixed-frequency",\n    is_flag=True,\n    default=False,\n    help="Allow -f 0 or multiple channels using Impinj's fixed-frequency extension.",\n)\n@click.option(\n    "--hoptable-id",\n''',
    count=3,
)
# Each of the three command functions has frequencies, hoptable_id in its signature.
text = read("sllurp/cli.py")
text, n = re.subn(
    r"(\n    frequencies,\n)(    hoptable_id,\n)",
    r"\1    impinj_fixed_frequency,\n\2",
    text,
)
if n != 3:
    raise RuntimeError(f"sllurp/cli.py: expected 3 command signatures, found {n}")
# Each Args field list and constructor gets the new field.
text, n = re.subn(
    r'(            "frequencies",\n)(            "hoptable_id",)',
    r'\1            "impinj_fixed_frequency",\n\2',
    text,
)
if n != 3:
    raise RuntimeError(f"sllurp/cli.py: expected 3 Args field lists, found {n}")
text, n = re.subn(
    r"(        frequencies=frequencies,\n)(        hoptable_id=hoptable_id,)",
    r"\1        impinj_fixed_frequency=impinj_fixed_frequency,\n\2",
    text,
)
if n != 3:
    raise RuntimeError(f"sllurp/cli.py: expected 3 Args constructors, found {n}")
write("sllurp/cli.py", text)

# Mask access password in debug output.
replace(
    "sllurp/cli.py",
    '''    logger.debug("access args: %s", args)\n    _access.main(args)\n''',
    '''    safe_args = args._replace(\n        access_password="***" if args.access_password else 0\n    )\n    logger.debug("access args: %s", safe_args)\n    _access.main(args)\n''',
)

# Wire explicit Impinj fixed-frequency config through all three verbs.
for path in ["sllurp/verb/inventory.py", "sllurp/verb/log.py", "sllurp/verb/access.py"]:
    replace(
        path,
        '''        frequencies={\n            "HopTableId": args.hoptable_id,\n            "ChannelList": frequency_list,\n            "Automatic": False,\n        },\n''',
        '''        frequencies={\n            "HopTableId": args.hoptable_id,\n            "ChannelList": frequency_list,\n            "Automatic": False,\n        },\n        impinj_fixed_frequency=args.impinj_fixed_frequency,\n''',
    )

# Access --time must actually bound the operation, and read/write are mutually exclusive.
replace(
    "sllurp/verb/access.py",
    '''    if not args.read_words and not args.write_words:\n        logger.info("Error: Either --read-words or --write-words has to be" " chosen.")\n        return 0\n''',
    '''    if args.read_words is not None and args.write_words is not None:\n        logger.error("Choose only one of --read-words or --write-words.")\n        return 2\n    if args.read_words is None and args.write_words is None:\n        logger.info("Error: Either --read-words or --write-words has to be chosen.")\n        return 2\n''',
)
replace(
    "sllurp/verb/access.py",
    '''    factory_args = dict(\n        report_every_n_tags=args.every_n,\n''',
    '''    factory_args = dict(\n        duration=args.time,\n        report_every_n_tags=args.every_n,\n''',
)
replace(
    "sllurp/verb/access.py",
    '''        start_inventory=True,\n        disconnect_when_done=True,\n''',
    '''        start_inventory=True,\n        disconnect_when_done=bool(args.time and args.time > 0),\n''',
)
replace(
    "sllurp/verb/access.py",
    '''        data = sys.stdin.buffer.read(args.write_words * 2)\n\n        opspec = C1G2Write(\n''',
    '''        expected_bytes = args.write_words * 2\n        data = sys.stdin.buffer.read(expected_bytes)\n        if len(data) != expected_bytes:\n            logger.error(\n                "Expected %d bytes on stdin for --write-words=%d, got %d",\n                expected_bytes,\n                args.write_words,\n                len(data),\n            )\n            reader.disconnect()\n            return\n\n        opspec = C1G2Write(\n''',
)

# --- Streaming CSV logger -------------------------------------------------
replace(
    "sllurp/verb/log.py",
    '''        self.rows = []\n        self.filehandle = filehandle\n        self.num_tags = 0\n''',
    '''        self.filehandle = filehandle\n        self.writer = csv.writer(self.filehandle, dialect="excel")\n        self.writer.writerow(("timestamp", "reader", "antenna", "rssi", "epc"))\n        self.num_tags = 0\n''',
)
replace(
    "sllurp/verb/log.py",
    '''            self.rows.append((timestamp, reader, antenna, rssi, epc))\n            self.num_tags += tag["TagSeenCount"]\n\n    def flush(self):\n        logger.info("Writing %d rows...", len(self.rows))\n        wri = csv.writer(self.filehandle, dialect="excel")\n        wri.writerow(("timestamp", "reader", "antenna", "rssi", "epc"))\n        wri.writerows(self.rows)\n''',
    '''            self.writer.writerow((timestamp, reader, antenna, rssi, epc))\n            self.num_tags += tag["TagSeenCount"]\n        self.filehandle.flush()\n\n    def flush(self):\n        self.filehandle.flush()\n''',
)

# --- EPC validation -------------------------------------------------------
replace(
    "sllurp/epc/sgtin_96.py",
    '''    if not sgtin_96:\n        raise Exception("Pass in a value.")\n\n    if not sgtin_96.startswith("30"):\n''',
    '''    if not sgtin_96:\n        raise ValueError("Pass in a value.")\n    if not isinstance(sgtin_96, str) or len(sgtin_96) != 24:\n        raise ValueError("SGTIN-96 must be exactly 24 hexadecimal characters.")\n    try:\n        int(sgtin_96, 16)\n    except ValueError as exc:\n        raise ValueError("SGTIN-96 must contain only hexadecimal characters.") from exc\n\n    if not sgtin_96.startswith("30"):\n''',
)
replace(
    "sllurp/epc/sgtin_96.py",
    '''        raise Exception("Not SGTIN-96.")\n''',
    '''        raise ValueError("Not SGTIN-96.")\n''',
)
replace(
    "sllurp/epc/sgtin_96.py",
    '''    if company_data > pow(10, l):\n        # can't be too large\n        raise Exception("Company value is too large")\n''',
    '''    if company_data >= pow(10, l):\n        raise ValueError("Company value is too large")\n''',
)
replace(
    "sllurp/epc/sgtin_96.py",
    '''    item_number = int(item_data, 2)\n    item_reference = str(item_number).zfill(k)\n''',
    '''    item_number = int(item_data, 2)\n    if item_number >= pow(10, k):\n        raise ValueError("Item reference value is too large")\n    item_reference = str(item_number).zfill(k)\n''',
)

# --- Packaging / CI hygiene ----------------------------------------------
replace("MANIFEST.in", "include README.md", "include README.rst")
replace(
    ".github/workflows/test.yml",
    "uses: actions/checkout@v4",
    "uses: actions/checkout@v6",
    count=3,
)
replace(
    ".github/workflows/test.yml",
    "uses: actions/setup-python@v5",
    "uses: actions/setup-python@v6",
    count=2,
)
replace(
    ".github/workflows/codespell.yml",
    '''  push:\n    branches: [develop]\n  pull_request:\n    branches: [develop]\n''',
    '''  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n''',
)
replace(
    ".github/workflows/codespell.yml",
    "uses: actions/checkout@v4",
    "uses: actions/checkout@v6",
)
replace(
    ".github/workflows/publish-to-pypi.yaml",
    "on: push",
    '''on:\n  push:\n    tags:\n      - "v*"\n  workflow_dispatch:\n''',
)
replace(
    ".gitignore",
    "# Installer logs\n",
    '''# Local secrets / reader TLS material\n.env\n.env.*\n!.env.example\n*.key\n*.pem\n*.p12\n*.pfx\n\n# Installer logs\n''',
)

# Avoid duplicate root logging handlers when CLI setup is called repeatedly.
replace(
    "sllurp/log.py",
    '''    root = logging.getLogger()\n    root.setLevel(loglevel)\n    root.addHandler(stderr_handler)\n''',
    '''    root = logging.getLogger()\n    root.setLevel(loglevel)\n    root.handlers.clear()\n    root.addHandler(stderr_handler)\n''',
)

# Existing regression test used implicit Impinj fixed-frequency behavior.
replace(
    "tests/test_regressions.py",
    '''            "frequencies": {\n                "HopTableId": 1,\n                "ChannelList": [1, 2],\n                "Automatic": False,\n            },\n''',
    '''            "frequencies": {\n                "HopTableId": 1,\n                "ChannelList": [1, 2],\n                "Automatic": False,\n            },\n            "impinj_fixed_frequency": True,\n''',
)

# --- Focused regression coverage -----------------------------------------
write(
    "tests/test_final_hardening.py",
    '''import io\nimport struct\nfrom types import SimpleNamespace\nfrom unittest.mock import Mock, patch\n\nimport pytest\n\nimport sllurp.llrp as llrp_module\nfrom sllurp.epc.sgtin_96 import parse_sgtin_96\nfrom sllurp.llrp import (\n    DEFAULT_MAX_MESSAGE_SIZE,\n    LLRPClient,\n    LLRPMessage,\n    LLRPReaderClient,\n    LLRPReaderConfig,\n    LLRPReaderState,\n)\nfrom sllurp.llrp_proto import LLRPError, LLRPROSpec, decode_param, msg_header_pack\nfrom sllurp.util import split_host_port\nfrom sllurp.verb import access as access_verb\nfrom sllurp.verb.log import CsvLogger\n\n\ndef base_config(**overrides):\n    values = {"start_inventory": False, "reset_on_connect": False}\n    values.update(overrides)\n    return LLRPReaderConfig(values)\n\n\ndef test_truncated_and_invalid_message_headers_are_rejected():\n    with pytest.raises(LLRPError, match="Invalid LLRP message header"):\n        LLRPMessage(msgbytes=b"\\x00")\n\n    reader = LLRPReaderClient("reader", config=base_config(max_message_size=100))\n    with pytest.raises(LLRPError, match="minimum"):\n        reader.raw_data_received(msg_header_pack(1, 5, 1))\n    with pytest.raises(LLRPError, match="exceeds configured maximum"):\n        reader.raw_data_received(msg_header_pack(1, 101, 1))\n\n\ndef test_truncated_and_invalid_parameters_raise_llrp_error():\n    # TV AntennaID needs two payload bytes after its one-byte header.\n    with pytest.raises(LLRPError, match="Truncated LLRP parameter"):\n        decode_param(bytes([0x80 | 1]))\n    # TLV length cannot be smaller than its own four-byte header.\n    with pytest.raises(LLRPError, match="Invalid LLRP parameter header"):\n        decode_param(struct.pack("!HH", 1, 2))\n\n\ndef test_message_size_default_is_bounded():\n    assert DEFAULT_MAX_MESSAGE_SIZE == 16 * 1024 * 1024\n    assert base_config().max_message_size == DEFAULT_MAX_MESSAGE_SIZE\n\n\ndef test_max_tari_is_applied_to_rospec():\n    mode = {"ModeIdentifier": 3, "MinTari": 10, "MaxTari": 20}\n    rospec = LLRPROSpec(mode, 1, tari=20, antennas=[1], tx_power={1: 1})\n    rf = rospec["AISpec"][0]["InventoryParameterSpec"][0]["AntennaConfiguration"][0]\n    assert rf["C1G2InventoryCommand"][0]["C1G2RFControl"]["Tari"] == 20\n\n\ndef test_impinj_fixed_frequency_requires_explicit_opt_in_in_reader_config():\n    frequencies = {"HopTableId": 1, "ChannelList": [1, 2], "Automatic": False}\n    with pytest.raises(LLRPError, match="impinj_fixed_frequency"):\n        base_config(frequencies=frequencies)\n\n    cfg = base_config(frequencies=frequencies, impinj_fixed_frequency=True)\n    client = LLRPClient(cfg, transport_tx_write=lambda _: None)\n    assert client._uses_impinj_extensions() is True\n\n\ndef test_duration_defaults_to_disconnect_and_schedules_timer(monkeypatch):\n    cfg = base_config(duration=2)\n    assert cfg.disconnect_when_done is True\n    created = []\n\n    class FakeTimer:\n        def __init__(self, delay, callback):\n            self.delay = delay\n            self.callback = callback\n            self.daemon = False\n            self.started = False\n            self.cancelled = False\n            created.append(self)\n\n        def start(self):\n            self.started = True\n\n        def cancel(self):\n            self.cancelled = True\n\n    monkeypatch.setattr(llrp_module, "Timer", FakeTimer)\n    reader = LLRPReaderClient("reader", config=cfg)\n    reader._on_llrp_state_changed(LLRPReaderState.STATE_INVENTORYING)\n    assert created[0].delay == 2\n    assert created[0].started is True\n    assert created[0].daemon is True\n    reader.hard_disconnect()\n    assert created[0].cancelled is True\n\n\ndef test_initial_connection_obeys_reconnect_policy(monkeypatch):\n    reader = LLRPReaderClient(\n        "reader",\n        config=base_config(reconnect=True, reconnect_retries=1, reconnect_delay=0),\n    )\n    calls = []\n\n    def connect_once_then_succeed():\n        calls.append(1)\n        if len(calls) == 1:\n            raise OSError("not ready")\n        return True\n\n    monkeypatch.setattr(reader, "_connect_socket", connect_once_then_succeed)\n    reader.connect(start_main_loop=False)\n    assert len(calls) == 2\n\n\ndef test_protocol_session_reset_drops_stale_deferreds():\n    reader = LLRPReaderClient("reader", config=base_config())\n    reader.llrp._deferreds["GET_READER_CONFIG_RESPONSE"].append(lambda *_: None)\n    reader.llrp.rospec = {"ROSpecID": 1}\n    reader._reset_protocol_session()\n    assert not reader.llrp._deferreds\n    assert reader.llrp.rospec is None\n\n\ndef test_second_request_for_same_response_is_rejected():\n    cfg = base_config()\n    client = LLRPClient(cfg, transport_tx_write=lambda _: None)\n    client._deferreds["GET_READER_CONFIG_RESPONSE"].append(lambda *_: None)\n    with pytest.raises(Exception, match="already pending"):\n        client.sendMessage({"GET_READER_CONFIG": {"RequestedData": 0}})\n\n\ndef test_tag_dispatcher_is_installed_even_after_raw_callback():\n    reader = LLRPReaderClient("reader", config=base_config())\n    raw_calls = []\n    tag_calls = []\n    reader.add_message_callback("RO_ACCESS_REPORT", lambda *_: raw_calls.append(1))\n    reader.add_tag_report_callback(lambda _reader, tags: tag_calls.append(tags))\n    msg = SimpleNamespace(\n        getName=lambda: "RO_ACCESS_REPORT",\n        msgdict={"RO_ACCESS_REPORT": {"TagReportData": [{"EPC-96": b"x" * 12}]}},\n    )\n    reader._on_llrp_message_received(msg)\n    assert raw_calls == [1]\n    assert len(tag_calls) == 1\n\n\ndef test_ipv6_host_parsing_and_socket_family():\n    assert split_host_port("[2001:db8::1]:55084", 5084) == ("2001:db8::1", 55084)\n    assert split_host_port("2001:db8::1", 5084) == ("2001:db8::1", 5084)\n\n    raw = Mock()\n    reader = LLRPReaderClient("2001:db8::1", config=base_config())\n    with patch("sllurp.llrp.socket", return_value=raw) as socket_factory:\n        reader._connect_socket()\n    socket_factory.assert_called_once_with(llrp_module.AF_INET6, llrp_module.SOCK_STREAM)\n\n\ndef test_access_time_is_forwarded_and_read_write_are_exclusive(monkeypatch):\n    args = SimpleNamespace(\n        host=("reader",), port=5084, time=3.5, every_n=None, antennas="1",\n        tx_power=0, tari=0, session=2, mode_identifier=None, population=4,\n        read_words=1, write_words=None, count=0, mb=3, word_ptr=0, access_password=0,\n        frequencies="1", hoptable_id=1, impinj_fixed_frequency=False,\n        tls_enabled=False, tls_verify=True, tls_ca_file=None, tls_client_cert=None,\n        tls_client_key=None, tls_server_hostname=None,\n    )\n    captured = []\n\n    class FakeReader:\n        def __init__(self, host, port, config):\n            captured.append(config)\n        def add_disconnected_callback(self, *args): pass\n        def add_tag_report_callback(self, *args): pass\n        def add_state_callback(self, *args): pass\n        def connect(self): pass\n        def is_alive(self): return False\n        def disconnect(self): pass\n\n    monkeypatch.setattr(access_verb, "LLRPReaderClient", FakeReader)\n    access_verb.main(args)\n    assert captured[0].duration == 3.5\n    assert captured[0].disconnect_when_done is True\n\n    args.read_words = 1\n    args.write_words = 1\n    assert access_verb.main(args) == 2\n\n\ndef test_csv_logger_streams_rows_instead_of_accumulating():\n    output = io.StringIO()\n    logger = CsvLogger(output)\n    reader = SimpleNamespace(get_peername=lambda: ("reader", 5084))\n    logger.tag_cb(\n        reader,\n        [{"EPC": "abc", "AntennaID": 1, "PeakRSSI": -40, "TagSeenCount": 1}],\n    )\n    text = output.getvalue()\n    assert "timestamp,reader,antenna,rssi,epc" in text\n    assert "reader:5084" in text\n    assert not hasattr(logger, "rows")\n\n\ndef test_sgtin96_rejects_wrong_length_and_invalid_decimal_partition_values():\n    with pytest.raises(ValueError, match="exactly 24"):\n        parse_sgtin_96("30")\n    with pytest.raises(ValueError, match="hexadecimal"):\n        parse_sgtin_96("30" + "z" * 22)\n''',
)

print("Final hardening patch applied")
