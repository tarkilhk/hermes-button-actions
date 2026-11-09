from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from button_actions import ActionContext
from button_actions.integrations.reminder_inbox import ReminderInbox

ID = "00000000-0000-4000-8000-000000000001"
CLICK = ActionContext("ri", "confirm", ID, "7", "-100123", "42", 12)


def provider(home):
    return ReminderInbox({"executable": str(home / "reminder-inbox"), "cwd": str(home),
                          "db_path": str(home / "synthetic.sqlite3")}, home)


@pytest.mark.parametrize("success", [True, False])
async def test_nested_cli_envelope(isolated_home, success):
    action = provider(isolated_home)
    action.run = AsyncMock(side_effect=[
        (0, {"ok": True, "data": {"id": ID, "chat_id": "-100123", "thread_id": "42"}}),
        (0 if success else 1, {"ok": success, "data": {"ok": success, "answer_text": "Confirmed" if success else "Action failed",
             "edit_message_text": "Updated" if success else "secret exception", "remove_keyboard": True}})])
    result = await action(CLICK)
    assert result.success is success
    assert result.remove_buttons is success
    assert result.edit_text == ("Updated" if success else None)
    assert action.run.call_count == 2
    assert action.run.call_args.args == ("operator", "telegram-callback", "ri:confirm:" + ID)


@pytest.mark.parametrize("changes", [{"payload": "bad;command"}, {"payload": ID + ":extra"}, {"action": "delete"}, {"namespace": "other"}])
async def test_invalid_callback_never_spawns(isolated_home, changes):
    action = provider(isolated_home)
    action.run = AsyncMock()
    assert not (await action(replace(CLICK, **changes))).success
    action.run.assert_not_awaited()


@pytest.mark.parametrize("owner", [{"chat_id": "other", "thread_id": "42"}, {"chat_id": "-100123", "thread_id": "other"}, {}])
async def test_draft_ownership_before_mutation(isolated_home, owner):
    action = provider(isolated_home)
    action.run = AsyncMock(return_value=(0, {"ok": True, "data": {"id": ID, **owner}}))
    assert not (await action(CLICK)).success
    action.run.assert_awaited_once_with("draft", "show", ID)


async def test_real_cli_round_trip_and_repeats(synthetic_inbox, isolated_home):
    options, cli, draft = synthetic_inbox
    action = ReminderInbox(options, isolated_home)
    confirm = draft()
    click = replace(CLICK, payload=confirm["id"])
    result = await action(click)
    assert result.success and result.remove_buttons and "confirmed" in result.text
    assert cli("draft", "show", confirm["id"])["status"] == "confirmed"
    assert not (await action(click)).success  # Preserve CLI refusal of an already resolved draft.
    cancel = draft()
    click = replace(click, payload=cancel["id"], action="cancel")
    assert (await action(click)).success
    assert not (await action(click)).success
    assert cli("draft", "show", cancel["id"])["status"] == "deleted"
    conflict = await action(replace(click, action="confirm"))
    assert not conflict.success and not conflict.remove_buttons
    foreign = draft(thread_id="43")
    assert not (await action(replace(click, payload=foreign["id"]))).success
    assert cli("draft", "show", foreign["id"])["status"] == "pending"
