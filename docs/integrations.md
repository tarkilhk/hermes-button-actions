# Integration author API

An integration is trusted Python code, imported during plugin registration from
explicit profile-local settings. Module names never come from callback data.
Relative names such as `.integrations.demo` resolve inside this plugin's
`button_actions` package; absolute importable module names also work. There is
no dependency on another plugin's load order.

## Register an action

Place a module at `button_actions/integrations/example.py` in the plugin copy:

```python
from ..router import ActionResult


def register(router, options, *, profile_home):
    async def acknowledge(click):
        if click.payload != "example-123":
            return ActionResult(False, "Unknown example item.")
        return ActionResult(True, "Example item acknowledged.")

    router.namespace(
        "example", chat_id=options["chat_id"], thread_id=options["thread_id"]
    ).action("acknowledge", acknowledge)
```

Add an item under `plugins.entries.button-actions.settings.integrations`:

```yaml
- module: .integrations.example
  options:
    chat_id: "REPLACE_WITH_CHAT_ID"
    thread_id: null
```

`example:acknowledge:example-123` now reaches this action through the same user
authorization, scope check, deadline, and feedback path. The bundled
[demo](../button_actions/integrations/demo.py) accepts item identifiers matching
`[A-Za-z0-9_-]{1,48}` and only returns a safe acknowledgment.

## Registry and data contracts

`router.namespace(name, *, chat_id, thread_id)` returns a namespace.
`namespace.action(name, async_handler)` registers a handler and returns the
namespace, allowing chaining. This is this project's API, not a new Hermes
context method. Keys match `[a-z][a-z0-9_]*`. Duplicate namespace/action pairs,
conflicting scopes, and verified Hermes core namespaces (including `mb*` and
`mx*`) are rejected. Reusing a namespace with the same scope is allowed.

The router splits callback strings with `split(':', 2)`, preserving colons in the
payload. Only registered namespace/action prefixes match the native handler.
Unmatched keys fall through to Hermes' existing callback handler. Do not register
core prefixes or patch the core callback router.

`ActionContext` is an immutable dataclass:

| Field | Type / meaning |
| --- | --- |
| `namespace`, `action`, `payload` | Strings from the routed callback |
| `user_id`, `chat_id` | String IDs |
| `thread_id` | String ID or `None` |
| `message_id` | Integer ID of the button message |

Handlers are async and return
`ActionResult(success, text, edit_text=None, remove_buttons=False)`. `success` is
a boolean; `text` is safe, nonempty destination-chat feedback. `edit_text` may
replace the button message; `remove_buttons=True` removes its keyboard. These
fields are not a transaction: integrations must only request edits appropriate
for the outcome. All output is plain text (`parse_mode=None`). Keep output
bounded and avoid credentials, raw exceptions, or sensitive item contents.

`profile_home` is the resolved Hermes profile captured during registration. The
callback runs with the Hermes home context override restored to that profile
and reset afterward. Keep relative imports for the bundled dataclasses: Hermes
loads plugins under profile-specific package names.

## Execution responsibilities

The gateway first authorizes the user through private adapter hooks, then the
plugin enforces exact scope. Accepted callbacks receive one early acknowledgment;
the result is a new message in the same chat/topic, not a second callback answer.
Edits and feedback delivery can fail independently of an action's outcome.
Telegram client timeouts cover UI operations; the action deadline covers the
handler only.

Validate payloads and domain ownership before mutations. Telegram callback data
is limited to 64 UTF-8 bytes; the router does not enforce that outbound limit or
create initial buttons. Send short identifiers rather than secrets. Callback data
is untrusted and may be replayed; authorization and scoping do not imply freshness.

Avoid blocking the event loop. Honor cancellation, clean up spawned processes,
and do not swallow cancellation to continue a mutation. This plugin provides no
locking, persistent state, queue, retry policy, rollback, idempotency, or
exactly-once execution. Concurrent clicks can reach your handler. Any such
properties must come from your domain implementation and be documented there.

Trusted Python integrations can call their own reviewed APIs, but this release
ships no generic HTTP/webhook provider or callback-controlled executable/module
selection. In-process code can access the process and filesystem: configuration
and imported code are part of the trust boundary.
