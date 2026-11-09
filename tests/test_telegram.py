import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from button_actions import ActionResult, Router
from button_actions.telegram import wire

pytestmark = pytest.mark.usefixtures("hermes_constants_stub")


@pytest.mark.parametrize("missing", ["_callback_ctx", "_callback_authorized"])
def test_missing_private_api_fails_before_wiring(isolated_home, missing):
    adapter = SimpleNamespace(_callback_ctx=lambda query: {}, _callback_authorized=AsyncMock())
    delattr(adapter, missing)
    app = SimpleNamespace(add_handler=AsyncMock())
    with pytest.raises(RuntimeError, match="callback authorization API"):
        wire(app, adapter, Router(), isolated_home)
    app.add_handler.assert_not_called()


def setup(handler, home, *, authorized=True, chat_id=1, thread_id=42, timeout=1):
    router = Router(timeout=timeout)
    router.namespace("custom", chat_id=1, thread_id=42).action("click", handler)
    app = SimpleNamespace(add_handler=lambda h: handlers.append(h))
    handlers = []
    query = SimpleNamespace(data="custom:click:a:b", from_user=SimpleNamespace(id=7),
                            message=SimpleNamespace(message_id=12, reply_markup="buttons"),
                            answer=AsyncMock(), edit_message_text=AsyncMock(), edit_message_reply_markup=AsyncMock())

    async def auth(q, cb, denial):
        if not authorized:
            await q.answer(denial)
        return authorized

    adapter = SimpleNamespace(_callback_ctx=lambda q: {"chat_id": chat_id, "thread_id": thread_id},
                              _callback_authorized=auth)
    wire(app, adapter, router, home)
    context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))
    return handlers[0].callback, SimpleNamespace(callback_query=query), context


@pytest.mark.parametrize("kwargs", [{"authorized": False}, {"chat_id": 2}, {"thread_id": 43}, {"thread_id": None}])
async def test_auth_and_scope_reject(isolated_home, kwargs):
    action = AsyncMock()
    callback, update, ctx = setup(action, isolated_home, **kwargs)
    await callback(update, ctx)
    action.assert_not_awaited()
    update.callback_query.answer.assert_awaited_once()
    ctx.bot.send_message.assert_not_awaited()


async def test_success_edit_failure_does_not_change_outcome(isolated_home):
    action = AsyncMock(return_value=ActionResult(True, "Done", "Updated", True))
    callback, update, ctx = setup(action, isolated_home)
    update.callback_query.edit_message_text.side_effect = RuntimeError("secret")
    await callback(update, ctx)
    update.callback_query.answer.assert_awaited_once_with()
    action.assert_awaited_once()
    click = action.call_args.args[0]
    assert (click.payload, click.user_id, click.chat_id, click.thread_id, click.message_id) == ("a:b", "7", "1", "42", 12)
    assert ctx.bot.send_message.call_args.kwargs["text"] == "Done (Button message could not be updated.)"


@pytest.mark.parametrize("mode", ["failure", "exception", "timeout"])
async def test_failure_feedback_no_retry(isolated_home, mode):
    async def slow(click):
        await asyncio.sleep(1)

    action = AsyncMock(return_value=ActionResult(False, "Declined"))
    if mode == "exception":
        action.side_effect = RuntimeError("secret")
    elif mode == "timeout":
        action.side_effect = slow
    callback, update, ctx = setup(action, isolated_home, timeout=0.01)
    await callback(update, ctx)
    action.assert_awaited_once()
    update.callback_query.answer.assert_awaited_once_with()
    text = ctx.bot.send_message.call_args.kwargs["text"]
    assert "secret" not in text
    assert ("timed out" if mode == "timeout" else "could not" if mode == "exception" else "Declined") in text


async def test_remove_only_and_feedback_failure(isolated_home, caplog):
    action = AsyncMock(return_value=ActionResult(True, "Done", remove_buttons=True))
    callback, update, ctx = setup(action, isolated_home)
    ctx.bot.send_message.side_effect = RuntimeError("secret")
    await callback(update, ctx)
    update.callback_query.edit_message_reply_markup.assert_awaited_once_with(reply_markup=None)
    update.callback_query.answer.assert_awaited_once()
    assert "secret" not in caplog.text
