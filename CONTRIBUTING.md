# Contributing

Keep changes small and describe the user-visible behavior and its trust boundary.
Use synthetic data and reviewed placeholders in examples. Do not include private
paths, hostnames, email addresses, screenshots, tokens, or profile artifacts.

Follow [development and tests](docs/development.md). Run the unit suite and
`git diff --check`; run the full source integration suite when changing adapter
wiring, authorization, scope, or CLI behavior. Report actual results and skips,
including source revisions for compatibility changes. Do not claim live coverage
from fake-transport tests.

Preserve Hermes authorization, exact chat/topic scope, built-in callback
fallthrough, fixed-argv CLI execution, safe feedback, and no automatic retries.
Keep runtime dependencies limited to the host Hermes Telegram SDK. New
integrations must validate payloads and domain ownership, explain mutation and
timeout behavior, and include focused tests. Trusted Python modules are supported;
this release has no generic HTTP/webhook provider.

Update relevant documentation and the changelog when behavior changes. Route
security reports through [SECURITY.md](SECURITY.md).
