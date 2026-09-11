from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import Event, RLock, Timer


ACTION_CLIENT = "client"
ACTION_ROSPEC = "rospec"
ACTION_READER_CONFIG = "reader_config"
ACTION_RECONNECT = "reconnect"


# Unknown/new fields default to reconnect. That is deliberately conservative:
# adding a new configuration attribute must never silently become live-safe.
CONFIG_FIELD_POLICY = {
    # Client/runtime-only behavior.
    "disconnect_when_done": ACTION_CLIENT,
    "max_message_size": ACTION_CLIENT,
    "reconnect": ACTION_CLIENT,
    "reconnect_retries": ACTION_CLIENT,
    "reconnect_delay": ACTION_CLIENT,
    "start_inventory": ACTION_CLIENT,
    "reset_on_connect": ACTION_CLIENT,
    "request_timeout": ACTION_CLIENT,
    # ROSpec / inventory behavior.
    "duration": ACTION_ROSPEC,
    "tari": ACTION_ROSPEC,
    "session": ACTION_ROSPEC,
    "mode_identifier": ACTION_ROSPEC,
    "tag_population": ACTION_ROSPEC,
    "report_every_n_tags": ACTION_ROSPEC,
    "report_timeout_ms": ACTION_ROSPEC,
    "dedup_seconds": ACTION_ROSPEC,
    "dedup_backend": ACTION_ROSPEC,
    "dedup_max_entries": ACTION_ROSPEC,
    "antennas": ACTION_ROSPEC,
    "tx_power": ACTION_ROSPEC,
    "tx_power_dbm": ACTION_ROSPEC,
    "tag_filter_mask": ACTION_ROSPEC,
    "tag_content_selector": ACTION_ROSPEC,
    "frequencies": ACTION_ROSPEC,
    "impinj_fixed_frequency": ACTION_ROSPEC,
    "impinj_search_mode": ACTION_ROSPEC,
    "impinj_reports": ACTION_ROSPEC,
    "impinj_tag_content_selector": ACTION_ROSPEC,
    # SET_READER_CONFIG behavior.
    "event_selector": ACTION_READER_CONFIG,
    "gpi_ports_config": ACTION_READER_CONFIG,
    "keepalive_interval": ACTION_READER_CONFIG,
    "impinj_event_selector": ACTION_READER_CONFIG,
    # Transport/session setup behavior.
    "socket_receive_buffer_bytes": ACTION_RECONNECT,
    "tls_enabled": ACTION_RECONNECT,
    "tls_verify": ACTION_RECONNECT,
    "tls_ca_file": ACTION_RECONNECT,
    "tls_client_cert": ACTION_RECONNECT,
    "tls_client_key": ACTION_RECONNECT,
    "tls_server_hostname": ACTION_RECONNECT,
    "impinj_extended_configuration": ACTION_RECONNECT,
}


def snapshot_config(config):
    """Return a detached public-field snapshot of a reader config object."""
    return {
        name: deepcopy(value)
        for name, value in vars(config).items()
        if not name.startswith("_")
    }


@dataclass(frozen=True)
class ConfigChange:
    field: str
    old: object
    new: object
    action: str


@dataclass(frozen=True)
class ConfigTransitionPlan:
    changes: tuple[ConfigChange, ...] = ()

    @property
    def is_noop(self):
        return not self.changes

    @property
    def actions(self):
        return frozenset(change.action for change in self.changes)

    @property
    def requires_rospec_restart(self):
        return ACTION_ROSPEC in self.actions

    @property
    def requires_reader_config_write(self):
        return ACTION_READER_CONFIG in self.actions

    @property
    def requires_reconnect(self):
        return ACTION_RECONNECT in self.actions

    @property
    def client_only(self):
        return bool(self.changes) and self.actions == {ACTION_CLIENT}


def build_config_transition_plan(old_config, new_config):
    old = snapshot_config(old_config)
    new = snapshot_config(new_config)
    changes = []
    for field_name in sorted(set(old) | set(new)):
        old_value = old.get(field_name)
        new_value = new.get(field_name)
        if old_value == new_value:
            continue
        action = CONFIG_FIELD_POLICY.get(field_name, ACTION_RECONNECT)
        changes.append(ConfigChange(field_name, old_value, new_value, action))
    return ConfigTransitionPlan(tuple(changes))


@dataclass
class ConfigTransition:
    plan: ConfigTransitionPlan
    old_config: object
    new_config: object
    status: str = "pending"
    error: str | None = None
    _done: Event = field(default_factory=Event, repr=False)

    @property
    def done(self):
        return self._done.is_set()

    @property
    def succeeded(self):
        return self.status == "success"

    def succeed(self):
        self.status = "success"
        self.error = None
        self._done.set()
        return self

    def fail(self, error):
        self.status = "failed"
        self.error = str(error)
        self._done.set()
        return self

    def wait(self, timeout=None):
        self._done.wait(timeout)
        return self.done


@dataclass
class PendingRequest:
    response_name: str
    message_id: int
    callback: object = None
    timer: object = None


class PendingRequestRegistry:
    """Thread-safe exact request/response correlation with stale-response memory."""

    def __init__(self, stale_limit=512):
        self._lock = RLock()
        self._pending = {}
        self._stale = []
        self._stale_set = set()
        self._stale_limit = max(1, int(stale_limit))

    def _remember_stale(self, key):
        if key in self._stale_set:
            return
        self._stale.append(key)
        self._stale_set.add(key)
        while len(self._stale) > self._stale_limit:
            old = self._stale.pop(0)
            self._stale_set.discard(old)

    def register(
        self,
        response_name,
        message_id,
        callback=None,
        timeout=None,
        on_timeout=None,
    ):
        key = (response_name, int(message_id))
        with self._lock:
            if key in self._pending:
                raise ValueError(f"pending request already registered: {key!r}")
            pending = PendingRequest(response_name, int(message_id), callback)
            self._pending[key] = pending
            self._stale_set.discard(key)
            if key in self._stale:
                self._stale.remove(key)
            if timeout is not None:
                timer = Timer(float(timeout), self._expire, args=(key, on_timeout))
                timer.daemon = True
                pending.timer = timer
                timer.start()
            return pending

    def _expire(self, key, on_timeout):
        pending = None
        with self._lock:
            pending = self._pending.pop(key, None)
            if pending is None:
                return
            pending.timer = None
            self._remember_stale(key)
        if on_timeout is not None:
            on_timeout(pending)

    def pop(self, response_name, message_id):
        key = (response_name, int(message_id))
        with self._lock:
            pending = self._pending.pop(key, None)
            if pending is None:
                return None
            if pending.timer is not None:
                pending.timer.cancel()
                pending.timer = None
            self._remember_stale(key)
            return pending

    def pop_response_type(self, response_name):
        """Pop the sole request of a response type, otherwise leave state untouched."""
        with self._lock:
            matches = [key for key in self._pending if key[0] == response_name]
            if len(matches) != 1:
                return None
            key = matches[0]
            pending = self._pending.pop(key)
            if pending.timer is not None:
                pending.timer.cancel()
                pending.timer = None
            self._remember_stale(key)
            return pending

    def cancel(self, response_name, message_id, remember_stale=True):
        key = (response_name, int(message_id))
        with self._lock:
            pending = self._pending.pop(key, None)
            if pending is None:
                return None
            if pending.timer is not None:
                pending.timer.cancel()
                pending.timer = None
            if remember_stale:
                self._remember_stale(key)
            return pending

    def cancel_all(self, remember_stale=False):
        with self._lock:
            values = list(self._pending.values())
            self._pending.clear()
            for pending in values:
                if pending.timer is not None:
                    pending.timer.cancel()
                    pending.timer = None
                if remember_stale:
                    self._remember_stale((pending.response_name, pending.message_id))
            if not remember_stale:
                self._stale.clear()
                self._stale_set.clear()
            return values

    def contains(self, response_name, message_id):
        with self._lock:
            return (response_name, int(message_id)) in self._pending

    def has_response_type(self, response_name):
        with self._lock:
            return any(key[0] == response_name for key in self._pending)

    def is_stale(self, response_name, message_id):
        with self._lock:
            return (response_name, int(message_id)) in self._stale_set

    def __len__(self):
        with self._lock:
            return len(self._pending)
