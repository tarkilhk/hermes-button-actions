# Setup

## Requirements and installation

Use a reviewed Hermes installation with its Telegram platform and native SDK
available. Python 3.11+ is required by this project. Testing covers Linux only.
The plugin manifest declares `requires_hermes: ">=0.23.0"` conservatively; the
exact tested Hermes source is `21ae0e1238fdf466fa52a85a6ebf75d6899e49da`.
Older/newer releases have not been exhaustively checked. Private adapter hooks
can drift independently of that version requirement.

Follow the copy commands in the [README](../README.md) from the repository root.
Copy only `__init__.py`, `plugin.yaml`, and the `button_actions` package into the
intended profile's `plugins/button-actions` directory. The plugin needs no
runtime pip dependencies beyond the host Hermes Telegram SDK. SDK imports are
lazy, when the native handler factory is wired. Installing the Python package
alone does not install the directory-plugin entry point and manifest for Hermes.

Review existing directory contents before replacing an installed copy. Merge
configuration rather than replacing the profile's entire `plugins` section.
**`plugins.isolation: in_process` is required**: native handler factories do not
work in `host` isolation. This setting affects the profile's plugin isolation;
review other enabled plugins before changing it.

## Scope and activation

Settings live at `plugins.entries.button-actions.settings`:

| Setting | Meaning |
| --- | --- |
| `timeout_seconds` | Positive finite number; default 10, covering one provider action |
| `integrations` | List of trusted `{module, options}` mappings; default `[]` |
| Integration `chat_id` | Explicit destination chat ID; quoted string recommended |
| Integration `thread_id` | Explicit topic ID or YAML `null` for no topic |

For the demo, use [example-config.yaml](../example-config.yaml). Replace
`REPLACE_WITH_CHAT_ID` with a chat ID you have reviewed, and use a quoted topic ID
if targeting a forum topic. `null` matches only messages without a thread. Missing
scope is never a wildcard. The same namespace cannot have conflicting scopes.
Inline callbacks without a chat message cannot execute actions.

Hermes must also authorize the clicking user under the gateway's existing policy.
This plugin adds a scope check; it never adds users to an allowlist. Keep initial
button messages in the same scope. Do not put secrets in callback data.

Merge the settings without adding `button-actions` to `plugins.enabled`, preserving
other enabled plugins. The enable command must make a new selection for hot
activation; an already-selected plugin may return "already enabled" without
rewiring the running gateway.

Enable with `hermes --profile YOUR_PROFILE plugins enable button-actions`, omitting
the profile flag for the default profile. Current Hermes can hot-activate the
registered callback factory. Verify the activation result and the profile gateway
log's `Wired native handlers from plugin 'button-actions'` entry. A fresh CLI
registration probe alone does not prove the running gateway loaded the handler.
If your version requires a restart, use your normal operational procedure.
No plugin code starts, restarts, or reconfigures a gateway. Confirm handler removal
after disabling or removing the plugin; a gateway restart may be necessary on
versions without symmetric handler unloading. An empty integration list registers
no native handler.

The local manifest's schema checks top-level setting types and issues warnings;
it is not a complete nested schema or a security sandbox. Custom Python module
names and arbitrary integration options are deliberately supported. Runtime
registration enforces registry constraints and providers validate their inputs.

## Optional Reminder Inbox

Install and review Reminder Inbox separately. Replace every absolute path below
with a reviewed local value. Add this item to `settings.integrations` (alongside
or instead of the demo); do not add an HTTP endpoint:

```yaml
- module: .integrations.reminder_inbox
  options:
    executable: /ABSOLUTE/PATH/TO/REVIEWED/venv/bin/reminder-inbox
    cwd: /ABSOLUTE/PATH/TO/REVIEWED/reminder-inbox
    db_path: /ABSOLUTE/PATH/TO/REVIEWED/reminder_inbox.sqlite3
    chat_id: "REPLACE_WITH_CHAT_ID"
    thread_id: "REPLACE_WITH_TOPIC_ID" # Or null for no topic.
```

All three paths are required and must be absolute. The executable is invoked
with fixed argv, without a shell:

```text
reminder-inbox draft show DRAFT_UUID --json
reminder-inbox operator telegram-callback ri:ACTION:DRAFT_UUID --json
```

Only canonical UUIDs and actions `confirm`/`cancel` are accepted. The read result
must match the requested draft ID and exact chat/topic before the mutation runs.
Both commands use explicit `cwd`, the captured profile's `HERMES_HOME`, and
`REMINDER_INBOX_DB_PATH`. Only `HOME` and `TMPDIR` are inherited; `PATH` is the OS
default, and gateway credentials are not forwarded. Reminder Inbox may load its
own project `.env`; review that directory and file. The explicit database
variable takes precedence in the tested CLI.

The plugin never imports SQLite or writes the database directly. CLI responses
use the nested `data` envelope, including error responses. Safe `answer_text`
becomes feedback; only successful results may edit the message/remove its keyboard.
Raw CLI error edit text is suppressed. Repeated resolved clicks preserve the
CLI's refusal; cancel stores `deleted`. There is no plugin idempotency layer.

The action deadline covers both commands together. Cancellation kills and reaps
the running process, but cannot roll back a mutation that already happened.
**Timeouts and unexpected exceptions can leave the mutation outcome unknown.**
Check domain state before manually repeating an action; there are no automatic
retries or exactly-once guarantees. See [security](security.md).
