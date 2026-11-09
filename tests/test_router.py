import pytest

from button_actions import ActionResult, Router, register


async def handler(click):
    return ActionResult(True, click.payload)


def test_registry_and_custom_payload():
    router = Router()
    ns = router.namespace("custom", chat_id="1", thread_id=None)
    ns.action("click", handler)
    assert router.namespace("custom", chat_id=1, thread_id=None) is ns
    assert router.resolve("custom:click:one:two") == (ns, handler, "click", "one:two")
    assert router.resolve("custom:missing:payload") is None
    assert router.resolve("custom:click") is None
    assert router.resolve(None) is None
    assert ns.allows(1, None) and not ns.allows(1, "42")
    with pytest.raises(ValueError, match="Duplicate"):
        ns.action("click", handler)
    with pytest.raises(ValueError, match="different scope"):
        router.namespace("custom", chat_id=2, thread_id=None)


@pytest.mark.parametrize("key", ["", "bad:key", "UPPER", "x.*", "ea", "gt", "cp", "mp", "mpg", "mpv", "mm", "mc", "mg", "cl", "sc", "update_prompt", "mb", "mbother", "mx"])
def test_invalid_and_builtin_namespaces(key):
    with pytest.raises(ValueError):
        Router().namespace(key, chat_id=1, thread_id=None)


@pytest.mark.parametrize("key", ["", "bad:key", "UPPER", "x.*"])
def test_invalid_actions(key):
    with pytest.raises(ValueError):
        Router().namespace("custom", chat_id=1, thread_id=None).action(key, handler)


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), True, "10"])
def test_invalid_timeouts(timeout):
    with pytest.raises(ValueError):
        Router(timeout=timeout)


def test_register_without_telegram_sdk(monkeypatch, hermes_constants_stub):
    import sys
    from types import SimpleNamespace

    monkeypatch.setitem(sys.modules, "telegram", None)
    factories = []
    config = {"integrations": [{"module": ".integrations.demo", "options": {
        "chat_id": "1", "thread_id": None}}]}
    register(SimpleNamespace(get_config=lambda key, default: config.get(key, default),
                             register_platform_handler=lambda *args: factories.append(args)))
    assert len(factories) == 1 and factories[0][0] == "telegram"
