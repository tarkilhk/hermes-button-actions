"""Reminder Inbox CLI provider. No direct database access or Telegram imports."""

import asyncio
import json
import os
from pathlib import Path
from uuid import UUID

from ..router import ActionResult


class ReminderInbox:
    def __init__(self, options, profile_home):
        self.executable = options["executable"]
        self.cwd = options["cwd"]
        self.db_path = options["db_path"]
        if not all(Path(p).is_absolute() for p in (self.executable, self.cwd, self.db_path)):
            raise ValueError("executable, cwd and db_path must be absolute paths")
        # Only the local CLI's state/profile inputs; do not forward gateway credentials.
        self.env = {key: os.environ[key] for key in ("HOME", "TMPDIR") if key in os.environ}
        self.env.update(PATH=os.defpath, HERMES_HOME=str(profile_home), REMINDER_INBOX_DB_PATH=self.db_path,
                        PYTHONDONTWRITEBYTECODE="1")

    async def run(self, *args):
        process = await asyncio.create_subprocess_exec(
            self.executable, *args, "--json", cwd=self.cwd, env=self.env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            stdout, _ = await process.communicate()
        except BaseException:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            await process.communicate()
            raise
        envelope = json.loads(stdout)
        if not isinstance(envelope, dict) or not isinstance(envelope.get("ok"), bool):
            raise ValueError("Invalid Reminder Inbox envelope")
        return process.returncode, envelope

    async def __call__(self, click):
        try:
            if click.namespace != "ri" or click.action not in {"confirm", "cancel"} or str(UUID(click.payload)) != click.payload:
                raise ValueError
        except ValueError:
            return ActionResult(False, "Invalid Reminder Inbox button.")

        code, envelope = await self.run("draft", "show", click.payload)
        draft = envelope.get("data")
        if code != 0 or envelope["ok"] is not True or not isinstance(draft, dict):
            return ActionResult(False, "Reminder draft could not be read.")
        if (draft.get("id") != click.payload or str(draft.get("chat_id")) != click.chat_id
                or (str(draft["thread_id"]) if draft.get("thread_id") is not None else None) != click.thread_id):
            return ActionResult(False, "This reminder draft belongs to a different chat/topic.")

        code, envelope = await self.run("operator", "telegram-callback", f"ri:{click.action}:{click.payload}")
        data = envelope.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("ok"), bool):
            raise ValueError("Invalid Reminder Inbox callback result")
        success = code == 0 and envelope["ok"] is True and data["ok"] is True
        text = data.get("answer_text")
        if not isinstance(text, str) or not text:
            text = "Reminder action completed." if success else "Reminder Inbox action failed."
        # CLI error edit text includes raw exception details; only use its safe answer text.
        edit = data.get("edit_message_text") if success else None
        if edit is not None and not isinstance(edit, str):
            edit = None
        return ActionResult(success, text, edit, success and data.get("remove_keyboard") is True)


def register(router, options, *, profile_home):
    provider = ReminderInbox(options, profile_home)
    namespace = router.namespace("ri", chat_id=options["chat_id"], thread_id=options["thread_id"])
    namespace.action("confirm", provider).action("cancel", provider)
