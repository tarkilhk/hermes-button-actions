# Development and tests

Work from a reviewed local checkout. Do not use a live Hermes profile, Telegram
bot, Reminder Inbox database, or a real project `.env` for tests. Tests do not
start the gateway or poll Telegram. Ordinary core/demo tests need no Hermes or
Reminder Inbox checkout.

## Unit suite

For a new development environment (the install commands may download packages):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install '.[test]'
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -rs
git diff --check
```

The `test` extra declares pytest, pytest-asyncio, and python-telegram-bot 22.8.
No host Hermes package is installed. Registration and Telegram bridge unit tests
use an explicit test-only `hermes_constants` double; router/demo tests run without
the framework. The source-dependent tests explicitly skip, with a reason, when
optional sources/dependencies are absent. Review `-rs` output; skips are not passes.

GitHub Actions runs this suite on Linux with Python 3.11 and 3.14, using full-SHA
pins for official checkout/setup-python actions. It does not fetch optional
application source checkouts or exercise a live deployment. A configured workflow
is not evidence of a successful hosted CI run.

## Full source integration suite

Use independently reviewed local source checkouts and the small declared test
extra. Do not install the entire Hermes runtime as a packaging dependency:

```bash
.venv/bin/python -m pip install '.[test,integration-test]'
export HERMES_SOURCE=/ABSOLUTE/PATH/TO/REVIEWED/hermes-agent
export REMINDER_INBOX_SOURCE=/ABSOLUTE/PATH/TO/REVIEWED/reminder-inbox
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -rs
git diff --check
```

The extra includes `ruamel.yaml==0.18.16`, PyYAML, python-dotenv, requests, rich,
platformdirs, and packaging for narrow framework/domain imports. Changing Hermes
source can change its import requirements; a missing optional dependency is an
explicit skip that must be resolved before claiming full integration coverage.
Unexpected API or behavior errors still fail. For a full verification run, expect
zero skips and record the exact source revisions and interpreter used.

The exact-source compatibility target for this release is Hermes
`21ae0e1238fdf466fa52a85a6ebf75d6899e49da`. The manifest's `>=0.23.0` is a
conservative declaration, not proof that all versions from that minimum work.
Private authorization hooks and core prefix reservations require rechecking on
upgrades. Testing is Linux-only; no other OS support is established.

## Isolation and coverage

Every test receives a temporary `HERMES_HOME`, empty bundled plugin directory,
and disabled project-plugin discovery. Parent Python socket connections are
forbidden. Full framework tests use the real PluginManager, native Telegram
adapter wiring/order, and PTB `Application.process_update` with a fake transport.
They cover initial registration and late handler hoisting, core fallthrough,
user authorization, exact scope, and domain callbacks without contacting Telegram.

The synthetic Reminder Inbox fixture copies only Python source files and
`schema.sql` into a temporary directory, never `.env`, data, or a source virtualenv.
It uses the test interpreter, a disposable database, restricted environment, and
a network-blocking module imported in each CLI child. No source-project state is
opened. The domain round trip checks confirm/cancel, resolved repeats, and a
foreign topic. CLI/provider unit tests mock execution and check envelopes and
ownership before mutation.

Other tests cover registry validation, custom payloads, safe demo acknowledgments,
single early callback acknowledgment, timeout/exception feedback without retries,
message edit failures, and feedback delivery failures. These checks do not prove
live Telegram delivery, production concurrency behavior, idempotency, or
exactly-once execution. No catalog submission or publication occurs in tests;
catalog validation with dependency installation is a separate release check.
