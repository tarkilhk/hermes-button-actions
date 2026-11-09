# Security reporting

Version 0.2.0 is the current release-preparation target. There is no established
long-term security support schedule. Review [security and trust](docs/security.md)
before enabling integrations, especially the private Hermes hooks and required
in-process execution.

If private vulnerability reporting is available on the
[repository's Security page](https://github.com/tarkilhk/hermes-button-actions/security),
use it. Otherwise open a minimal [issue](https://github.com/tarkilhk/hermes-button-actions/issues)
asking for a private reporting channel, without exploit details or sensitive data.
Do not include bot tokens, callback secrets, profile configuration, database
contents, or private logs in public issues. No response-time guarantee is offered.

A useful private report includes the affected version and Hermes source revision,
expected and observed authorization/scope behavior, and a minimal synthetic
reproduction. Avoid testing against real users or live domain state.
