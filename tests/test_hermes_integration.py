"""Real Hermes discovery, adapter wiring, PTB dispatch, and synthetic CLI state."""

import json
from pathlib import Path
import shutil

import pytest
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler
from telegram.request import BaseRequest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.usefixtures("hermes_source")


class FakeTelegram(BaseRequest):
    def __init__(self):
        self.calls = []

    @property
    def read_timeout(self):
        return 1

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def do_request(self, url, method, request_data=None, **kwargs):
        endpoint = url.rsplit("/", 1)[-1]
        params = request_data.parameters if request_data else {}
        self.calls.append((endpoint, params))
        if endpoint == "getMe":
            result = {"id": 99, "is_bot": True, "first_name": "Synthetic", "username": "synthetic_bot"}
        elif endpoint in {"sendMessage", "editMessageText"}:
            result = {"message_id": 12, "date": 1, "chat": {"id": int(params["chat_id"]), "type": "supergroup"},
                      "text": params["text"]}
        elif endpoint in {"answerCallbackQuery", "editMessageReplyMarkup"}:
            result = True
        else:
            raise AssertionError(f"Unexpected Telegram API method: {endpoint}")
        return 200, json.dumps({"ok": True, "result": result}).encode()


def update(bot, data, *, user_id=7, chat_id=-100123, thread_id=42, update_id=1):
    message = {"message_id": 12, "date": 1, "chat": {"id": chat_id, "type": "supergroup"}, "text": "Synthetic buttons"}
    if thread_id is not None:
        message["message_thread_id"] = thread_id
    return Update.de_json({"update_id": update_id, "callback_query": {
        "id": str(update_id), "chat_instance": "synthetic", "data": data,
        "from": {"id": user_id, "is_bot": False, "first_name": "Tester"}, "message": message}}, bot)


@pytest.mark.parametrize("late", [False, True], ids=["before-core", "late-hoisting"])
async def test_real_manager_native_dispatch_and_cli(isolated_home, synthetic_inbox, late):
    from gateway.config import PlatformConfig
    from hermes_cli.plugins import get_plugin_manager
    from plugins.platforms.telegram.adapter import TelegramAdapter

    options, cli, draft = synthetic_inbox
    plugin = isolated_home / "plugins" / "button-actions"
    plugin.mkdir(parents=True)
    for filename in ("__init__.py", "plugin.yaml"):
        shutil.copyfile(ROOT / filename, plugin / filename)
    shutil.copytree(ROOT / "button_actions", plugin / "button_actions", ignore=shutil.ignore_patterns("__pycache__"))
    # An independently configured namespace, proving there is no ri-specific router path.
    (plugin / "button_actions" / "integrations" / "probe.py").write_text(
        'from ..router import ActionResult\n'
        'from hermes_constants import get_hermes_home\n'
        'def register(router, options, *, profile_home):\n'
        '    async def click(ctx):\n'
        '        assert get_hermes_home() == profile_home\n'
        '        return ActionResult(True, "Custom " + ctx.payload)\n'
        '    router.namespace("tiny", chat_id="-100123", thread_id="42").action("ping", click)\n')
    config = {"plugins": {"enabled": ["button-actions"], "isolation": "in_process", "entries": {
        "button-actions": {"settings": {"integrations": [
            {"module": ".integrations.reminder_inbox", "options": options}, {"module": ".integrations.probe"}]}}}}}
    # JSON is a YAML subset; avoid a config-writing library in the plugin.
    (isolated_home / "config.yaml").write_text(json.dumps(config))
    manager = get_plugin_manager()
    manager.discover_and_load()
    info = next(p for p in manager.list_plugins() if p["name"] == "button-actions")
    assert info["enabled"] and not info["error"], info
    assert len(manager.get_platform_handler_factories("telegram")) == 1

    adapter = TelegramAdapter(PlatformConfig())
    authorizations = []

    def authorize(user_id, chat_type, chat_id, **kwargs):
        authorizations.append((user_id, chat_type, chat_id, kwargs.get("thread_id")))
        return user_id == "7"

    adapter.set_authorization_check(authorize)
    core = []
    observed = []

    async def core_callback(event, context):
        core.append(event.callback_query.data)

    async def observer(event, context):
        observed.append(event.update_id)

    # Keep the real handler table and PTB matching, with inert core/observer callbacks.
    adapter._handle_callback_query = core_callback
    adapter._on_platform_update = observer
    transport = FakeTelegram()
    app = Application.builder().token("99:SYNTHETIC").request(transport).get_updates_request(FakeTelegram()).build()
    errors = []

    async def error_handler(event, context):
        errors.append(context.error)

    app.add_error_handler(error_handler)
    if late:
        adapter._register_handlers(app)
    adapter._wire_plugin_handlers(app)
    if not late:
        adapter._register_handlers(app)
    adapter._wire_plugin_handlers(app)  # real idempotent rewire
    callbacks = [h for h in app.handlers[0] if isinstance(h, CallbackQueryHandler)]
    assert len(callbacks) == 2 and callbacks[0].pattern is not None and callbacks[1].pattern is None

    counter = 0

    async def dispatch(data, **kwargs):
        nonlocal counter
        counter += 1
        start = len(transport.calls)
        await app.process_update(update(app.bot, data, update_id=counter, **kwargs))
        assert not errors, errors
        return transport.calls[start:]

    try:
        await app.initialize()  # getMe goes only to FakeTelegram; never start polling.
        calls = await dispatch("tiny:ping:one:two")
        assert [m for m, _ in calls] == ["answerCallbackQuery", "sendMessage"]
        assert calls[-1][1]["text"] == "Custom one:two"
        assert authorizations[-1] == ("7", "forum", "-100123", "42")
        for data in ("ea:once:1", "gt:done:1", "mp:provider", "cp:choice", "tiny:unknown:x"):
            await dispatch(data)
            assert core[-1] == data
        for kwargs in ({"user_id": 8}, {"chat_id": -100999}, {"thread_id": 43}, {"thread_id": None}):
            calls = await dispatch("tiny:ping:x", **kwargs)
            assert [m for m, _ in calls] == ["answerCallbackQuery"]
        item = draft()
        calls = await dispatch("ri:confirm:" + item["id"])
        assert [m for m, _ in calls] == ["answerCallbackQuery", "editMessageText", "sendMessage"]
        assert calls[-1][1]["text"] == "Reminder confirmed"
        assert cli("draft", "show", item["id"])["status"] == "confirmed"
        calls = await dispatch("ri:confirm:" + item["id"])
        assert [m for m, _ in calls] == ["answerCallbackQuery", "sendMessage"]
        assert calls[-1][1]["text"] == "Reminder Inbox action failed"
        assert cli("draft", "show", item["id"])["status"] == "confirmed"
        assert len(observed) == counter
    finally:
        await app.shutdown()
        manager.unload()
