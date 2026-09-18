"""Deterministic timer support for concurrency tests."""


class ManualTimer:
    """A controllable replacement for ``threading.Timer`` in unit tests."""

    created = []

    def __init__(self, interval, function, args=None, kwargs=None):
        self.interval = interval
        self.function = function
        self.args = tuple(args or ())
        self.kwargs = dict(kwargs or {})
        self.daemon = False
        self.cancelled = False
        self.started = False
        type(self).created.append(self)

    @classmethod
    def reset(cls):
        """Discard timers retained by an earlier test."""
        cls.created.clear()

    def start(self):
        """Record that production code armed the timer."""
        self.started = True

    def cancel(self):
        """Prevent a later manual firing."""
        self.cancelled = True

    def fire(self):
        """Run the callback synchronously unless the timer was cancelled."""
        if not self.started or self.cancelled:
            return
        self.function(*self.args, **self.kwargs)

