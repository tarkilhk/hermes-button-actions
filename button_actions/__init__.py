"""Registration uses only stdlib; Telegram is imported when Hermes wires the factory."""

from importlib import import_module

from .router import ActionContext, ActionResult, Router


def register(ctx):
    from hermes_constants import get_hermes_home
    from .telegram import wire

    profile_home = get_hermes_home().resolve()
    router = Router(timeout=ctx.get_config("timeout_seconds", 10))
    for integration in ctx.get_config("integrations", []):
        # These are operator-trusted Python modules, never names from callback data.
        module = import_module(integration["module"], package=__package__)
        module.register(router, integration.get("options", {}), profile_home=profile_home)
    if router.keys:
        def factory(application, adapter):
            wire(application, adapter, router, profile_home)

        ctx.register_platform_handler("telegram", factory)


__all__ = ["ActionContext", "ActionResult", "Router", "register"]
