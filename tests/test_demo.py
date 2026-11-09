import asyncio
from types import SimpleNamespace

import pytest

from button_actions import ActionContext, Router, register
from button_actions.integrations.demo import register as register_demo


async def test_demo_acknowledges_item_without_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Demo must not start a process")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    monkeypatch.setattr(asyncio, "create_subprocess_shell", forbidden)
    router = Router()
    register_demo(router, {"chat_id": "1", "thread_id": None}, profile_home=None)
    namespace, handler, action, payload = router.resolve("demo:ping:example-123")
    assert namespace.allows("1", None)
    assert not namespace.allows("1", "42")
    assert not namespace.allows("2", None)
    result = await handler(ActionContext("demo", action, payload, "7", "1", None, 12))
    assert result.success and result.text == "Demo received item example-123."
    assert result.edit_text is None and not result.remove_buttons
    assert router.resolve("demo:unknown:example-123") is None


@pytest.mark.parametrize("payload", ["", "x" * 49, "one:two", "<secret>", "item\n"])
async def test_demo_rejects_invalid_identifiers(payload):
    router = Router()
    register_demo(router, {"chat_id": "1", "thread_id": "42"}, profile_home=None)
    _, handler, action, _ = router.resolve("demo:ping:" + payload)
    result = await handler(ActionContext("demo", action, payload, "7", "1", "42", 12))
    assert not result.success and result.text == "Invalid demo item identifier."


@pytest.mark.parametrize("options", [{}, {"chat_id": "1"}, {"thread_id": None}])
def test_demo_requires_explicit_scope(options):
    with pytest.raises(KeyError):
        register_demo(Router(), options, profile_home=None)


def test_no_integrations_means_no_factory(hermes_constants_stub):
    factories = []
    register(SimpleNamespace(get_config=lambda key, default: default,
                             register_platform_handler=lambda *args: factories.append(args)))
    assert factories == []
