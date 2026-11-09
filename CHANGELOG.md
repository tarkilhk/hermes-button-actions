# Changelog

## 0.2.0 — Unreleased

- Prepare public metadata and MIT licensing, with setup, API, trust, troubleshooting,
  and development documentation.
- Add an opt-in `demo:ping:example-123` acknowledgment integration with focused tests.
- Require explicit reviewed Reminder Inbox executable and working-directory paths;
  remove environment-specific source defaults from tests and examples.
- Separate portable unit checks from optional source integration tests, with
  explicit skips and synthetic CLI child network blocking.
- Add a Linux unit-test workflow with pinned official GitHub Actions.

The scoped callback router, native Hermes authorization path, optional fixed-argv
Reminder Inbox provider, and built-in callback fallthrough remain the foundation.
No HTTP provider, retry mechanism, or live deployment is introduced by this release.
