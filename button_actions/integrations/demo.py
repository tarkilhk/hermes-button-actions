"""Opt-in demonstration: acknowledge an item identifier without changing state."""

import re

from ..router import ActionResult


def register(router, options, *, profile_home):
    async def ping(click):
        # Keep feedback bounded and avoid echoing arbitrary callback content.
        if re.fullmatch(r"[A-Za-z0-9_-]{1,48}", click.payload) is None:
            return ActionResult(False, "Invalid demo item identifier.")
        return ActionResult(True, f"Demo received item {click.payload}.")

    router.namespace(
        "demo", chat_id=options["chat_id"], thread_id=options["thread_id"]
    ).action("ping", ping)
