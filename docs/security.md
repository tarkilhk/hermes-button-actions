# Security and operational trust

## Compatibility boundary

**Native SDK handler factories require `plugins.isolation: in_process`.** Host
isolation is unsupported. Registration uses the public
`ctx.register_platform_handler('telegram', factory)` API, but authorization uses
the adapter's **private `_callback_ctx` and `_callback_authorized` methods**.
The latter calls Hermes' callback-user authorization policy. Wiring refuses to
register if either method is missing; presence alone cannot prove unchanged
semantics. Retest callback authorization and handler ordering after Hermes upgrades.

The manifest conservatively requires Hermes `>=0.23.0`. Exact-source tests use
`21ae0e1238fdf466fa52a85a6ebf75d6899e49da`, not an exhaustive minimum-version
proof. Linux is the only tested platform. Initial wiring and late handler
hoisting are covered using fake Telegram transport; those tests do not establish
live gateway or multiplexed production behavior.

## What is checked

1. Only registered namespace/action prefixes reach the plugin handler. Reserved
   core namespaces are rejected and unmatched callbacks fall through to Hermes.
2. Hermes authorizes the clicking user under the existing gateway policy.
3. The callback must have a chat message and match the integration's exact
   configured chat ID and topic ID. `null` means no topic, never any topic.
4. The integration validates its payload and domain ownership before acting.
   Reminder Inbox checks canonical UUID/action and the draft's ID/chat/topic.

This plugin does not alter gateway allowlists. A click in scope is not proof that
the underlying domain item belongs to the user; each integration must check its
own rules. Replayed and concurrent clicks are possible. Telegram limits callback
data to 64 UTF-8 bytes; use identifiers, never secrets or executable instructions.

## Code and configuration are trusted

Integrations are Python modules selected by the operator and imported in process.
They have the host process's access to files, memory, and credentials. The schema
is advisory type validation, not isolation. Review modules, options, installed
files, executable paths, working directories, and permissions before activation.
There are no core monkeypatches or replacement adapters.

The manifest uses `capabilities: []`: the tested Hermes registry defines no
capability for native handler factories. The plugin does not call the gated
`ctx.platform_actions` API. An empty declaration does **not** imply that trusted
in-process code is restricted from making network requests or executing code.

The bundled demo only validates an identifier and constructs an acknowledgment.
Normal callback acknowledgment and feedback still go through Telegram. The
optional Reminder Inbox provider starts a reviewed executable with fixed argv
and a restricted environment, never a shell. It does not write SQLite directly.
Reminder Inbox may load a project `.env` from its configured source directory;
review that file as well as the explicit database destination.

## Outcomes and feedback

There is no plugin database, queue, workflow engine, retry loop, rollback,
idempotency guarantee, or exactly-once execution. A repeated click can invoke a
handler again. Reminder Inbox's existing state transitions decide whether a
repeated resolved action is refused.

A timeout or exception can occur after a domain mutation. Cancellation kills and
reaps a running CLI process but cannot undo a committed change. **Treat the
outcome as unknown and inspect domain state before manually repeating.** There
are no automatic retries. A successful callback acknowledgment only means the
click was accepted, not that the domain action completed.

Message edits and feedback delivery are separate network operations. An edit
failure is reported without converting a successful domain mutation into a claimed
failure. Undeliverable feedback is logged without raw exception details or
callback payloads; absence of a result message does not prove that nothing changed.
Integrations must return safe chat-visible text and avoid raw exception details.

See [SECURITY.md](../SECURITY.md) for reporting guidance and
[development](development.md) for synthetic test isolation.
