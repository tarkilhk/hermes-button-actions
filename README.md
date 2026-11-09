# Hermes Button Actions

Turn Telegram callback buttons into small, scoped actions for trusted Hermes
integrations. Route `namespace:action:payload` to Python handlers while keeping
Hermes authorization and an exact chat/topic boundary in front of every action.

Version **0.2.0** · [MIT](LICENSE) · [Source](https://github.com/tarkilhk/hermes-button-actions)

| Included | Boundary |
| --- | --- |
| Namespace/action routing and extensible Python handlers | Operator-trusted code running inside Hermes |
| Hermes user authorization, then exact chat/topic checks | Does not grant access or change gateway allowlists |
| Harmless bundled `demo:ping:example-123` integration | Explicit configuration required; acknowledges an item only |
| Optional Reminder Inbox CLI integration | Separate installation; fixed argv, no shell or direct database writes |
| Early acknowledgment, plain-text feedback, optional message edits | Timeouts can leave an unknown mutation outcome; no automatic retries |
| Native Telegram handler registration | **`in_process` only**, using the host's Telegram SDK |
| No additional plugin runtime packages | No plugin database, queue, workflow engine, or generic HTTP/webhook provider |

**Compatibility:** Linux-tested only; Python 3.11+. The manifest conservatively
requires Hermes `>=0.23.0`. Exact-source compatibility was tested against
`21ae0e1238fdf466fa52a85a6ebf75d6899e49da`; this is not an exhaustive proof of
minimum-version support. Authorization depends on the adapter's **private
`_callback_ctx` and `_callback_authorized` hooks**, which may drift. Review and
retest on Hermes upgrades. See [security and trust](docs/security.md).

## Quick start

Install the public repository into the intended profile, initially disabled:

```bash
hermes --profile YOUR_PROFILE plugins install tarkilhk/hermes-button-actions --no-enable
```

For the default profile, omit `--profile YOUR_PROFILE`. Review the source and
configuration before enabling. For a reviewed local copy, manual installation
also works. Replace the absolute profile path first:

```bash
profile_home=/ABSOLUTE/PATH/TO/REVIEWED/HERMES_PROFILE
plugin_dir="$profile_home/plugins/button-actions"
mkdir -p "$plugin_dir"
cp __init__.py plugin.yaml "$plugin_dir/"
cp -R button_actions "$plugin_dir/"
```

No pip or editable installation is needed for this copy-based setup. The host
Hermes Telegram runtime supplies `python-telegram-bot`; do not copy a virtualenv.
Merge [example-config.yaml](example-config.yaml) into that profile's `config.yaml`,
keeping existing entries and replacing the chat placeholder:

```yaml
plugins:
  isolation: in_process
  entries:
    button-actions:
      settings:
        timeout_seconds: 10
        integrations:
          - module: .integrations.demo
            options:
              chat_id: "REPLACE_WITH_CHAT_ID"
              thread_id: null # Only messages without a topic; use a quoted topic ID otherwise.
```

Merge only these settings, preserving any existing enabled-plugin list. Do not
add `button-actions` to `plugins.enabled` yet: the enable command below owns that
step and triggers hot activation. After reviewing the configuration, run:

```bash
hermes --profile YOUR_PROFILE plugins enable button-actions
```

Current Hermes can wire callbacks into the running gateway without a restart.
Check its activation result and the profile gateway log for
`Wired native handlers from plugin 'button-actions'`. If hot activation is not
available, use your normal gateway restart procedure. An empty `integrations`
list registers no handlers.
See [setup](docs/setup.md) for scope selection, lifecycle, and optional Reminder
Inbox configuration.

## Try the harmless demo

A **URL button** opens a link in the client. A **callback button** sends
`callback_data` to the bot; this plugin routes that data to a configured handler.
An HTTP-looking payload does not become a request. There is no generic HTTP or
webhook provider.

An existing trusted Python sender using the same Hermes bot can attach:

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

markup = InlineKeyboardMarkup([[
    InlineKeyboardButton("Acknowledge example", callback_data="demo:ping:example-123")
]])
# Pass reply_markup=markup when sending to the explicitly configured chat/topic.
```

The plugin handles clicks; it does not post the initial message. An authorized
click in the configured scope returns plain text: `Demo received item example-123.`
The demo stores nothing and invokes no CLI or network provider. Normal Telegram
acknowledgment and feedback still use the host bot transport.

Telegram limits `callback_data` to **64 UTF-8 bytes**. Use short item identifiers,
never secrets. Payloads preserve extra colons via `split(':', 2)`; each integration
must validate its own payload. Trusted Python integrations can extend the handler
registry without changing Hermes core.

## Documentation

- [Setup and optional providers](docs/setup.md)
- [Integration author API](docs/integrations.md)
- [Security, trust, and operational risks](docs/security.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Development and test isolation](docs/development.md)
- [Contributing](CONTRIBUTING.md), [security reporting](SECURITY.md), [changelog](CHANGELOG.md)
