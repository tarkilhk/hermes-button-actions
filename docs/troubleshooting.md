# Troubleshooting

| Symptom | Checks |
| --- | --- |
| Plugin absent | Confirm the intended profile, `plugins/button-actions/plugin.yaml` and root `__init__.py`, and `plugins.enabled` entry. Check Hermes load errors. |
| No action handler | Confirm `in_process` isolation, host Telegram SDK availability, and a nonempty configured integration list. Follow the activation sequence in setup and verify the gateway wiring log. |
| Enable says already enabled | Manually adding the plugin to `plugins.enabled` can skip hot activation. For an already-selected configuration, use your normal gateway restart procedure and verify wiring. For a fresh install, merge settings first and let the enable command select the plugin. |
| Private authorization API error | Check `_callback_ctx` / `_callback_authorized` compatibility with the installed Hermes source. Stop and retest the upgrade; do not bypass authorization. |
| Button opens a page | It is a URL button. Use `callback_data` on a button sent by the same bot for callback routing. |
| Click falls through | Check exact lowercase namespace/action registration and `namespace:action:payload` structure. Unknown keys intentionally reach Hermes. |
| Authorization denied | Review the existing gateway authorization policy for that user/chat/topic; plugin configuration grants no access. |
| Outside configured chat/topic | Review both IDs. YAML `null` only matches no topic; missing IDs are not wildcards. Inline callbacks without a message are unsupported. |
| Demo rejects the payload | Use an item identifier of 1–48 ASCII letters, digits, underscores, or hyphens, such as `example-123`. |
| Telegram rejects a button | Keep callback data within 64 UTF-8 bytes, including prefixes; multi-byte characters use more than one byte. |
| Reminder draft cannot be read | Review the explicit executable, cwd, database path, CLI JSON envelope, and CLI permissions locally. Do not post secrets or raw diagnostics into chat. |
| Timeout / unknown outcome | Inspect domain state before any manual repeat. Raising the deadline does not determine whether an earlier mutation happened. |
| Action succeeded but message is stale | Edits/removing buttons may have failed; feedback reports this separately. Check message permissions and age. |
| No final feedback | Feedback delivery may have failed after a mutation. Check safe gateway warnings and domain state before repeating. |
| Integration tests skipped | Use `pytest -rs` for the reason. Set source variables and install declared integration-test extras; skips are not compatibility evidence. |

Verify that disabling or removal unwires existing handlers. Versions without
symmetric handler unloading may require a gateway restart. This project does not restart the gateway.
See [setup](setup.md) and [security](security.md) before changing deployment or
retrying domain actions.
