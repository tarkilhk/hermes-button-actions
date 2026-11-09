"""Hermes directory-plugin entry point."""

def register(ctx):
    from .button_actions import register as register_actions

    register_actions(ctx)
