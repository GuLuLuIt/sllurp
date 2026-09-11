Runtime state and dynamic configuration
=======================================

Sllurp distinguishes configuration that the application *wants* from the
ROSpec generated from it and from configuration known to be active in the
current inventory session.

``LLRPClient.get_config_state()`` returns four views::

    desired            application configuration
    generated_rospec   snapshot used to build the cached ROSpec
    applied            snapshot active after inventory reaches INVENTORYING
    reported_reader    normalized fields returned by GET_READER_CONFIG

Dynamic configuration
---------------------

Use ``LLRPReaderClient.apply_config(new_config)`` for controlled runtime
changes.  Fields are classified before any reader state is mutated:

* client-only changes commit without reader traffic;
* ROSpec changes stop inventory, regenerate the ROSpec, and resume;
* SET_READER_CONFIG changes are serialized through the reader configuration
  request and then resume inventory when necessary;
* transport/session fields such as TLS require an explicit reconnect and are
  rejected while connected rather than being half-applied.

The returned ``ConfigTransition`` exposes ``status``, ``error`` and the
structured field-change plan.  An optional ``onCompletion`` callback receives
that transition when the asynchronous reader work reaches a terminal result.

Timed pause
-----------

``reader.llrp.pause(N)`` pauses an active ROSpec and starts its resume timer
only after the reader acknowledges ``DISABLE_ROSPEC``.  Explicit ``resume()``,
disconnect, session reset, and another pause invalidate stale timers.

Pending requests
----------------

Tracked requests are registered before bytes are written to the transport and
responses are correlated using both response type and LLRP message ID.  This
prevents a fast response from winning a race against callback registration and
prevents wrong-ID, stale, or duplicate responses from consuming the wrong
operation.

``LLRPReaderConfig.request_timeout`` may be set to a positive number of seconds
to enable request timeout callbacks.  It is ``None`` by default to preserve
legacy timing behavior.

Callback dispatch
-----------------

Callback registries are protected by an internal re-entrant lock.  Dispatch
captures an ordered snapshot under the lock and releases the lock before
calling application code.  Add/remove/clear operations during a dispatch
therefore affect the next dispatch cycle, never corrupt the current one.
