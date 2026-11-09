"""Small namespace/action registry; no Telegram or domain dependencies."""

import math
import re
from dataclasses import dataclass
from typing import Awaitable, Callable

# Core prefixes in the verified Hermes Telegram adapter. mb/mx match startswith.
_CORE = {"mp", "mpg", "mpv", "mm", "mc", "mg", "cp", "gt", "ea", "sc", "cl", "update_prompt"}
_KEY = re.compile(r"[a-z][a-z0-9_]*\Z")


@dataclass(frozen=True)
class ActionContext:
    namespace: str
    action: str
    payload: str
    user_id: str
    chat_id: str
    thread_id: str | None
    message_id: int


@dataclass(frozen=True)
class ActionResult:
    success: bool
    text: str
    edit_text: str | None = None
    remove_buttons: bool = False


Handler = Callable[[ActionContext], Awaitable[ActionResult]]


class Namespace:
    def __init__(self, router, name, chat_id, thread_id):
        self.router, self.name = router, name
        self.chat_id, self.thread_id = chat_id, thread_id

    def action(self, name: str, handler: Handler):
        if not isinstance(name, str) or not _KEY.fullmatch(name) or not callable(handler):
            raise ValueError("Invalid action registration")
        key = (self.name, name)
        if key in self.router._actions:
            raise ValueError("Duplicate namespace/action")
        self.router._actions[key] = (self, handler)
        return self

    def allows(self, chat_id, thread_id):
        return str(chat_id) == self.chat_id and (
            str(thread_id) if thread_id is not None else None
        ) == self.thread_id


class Router:
    def __init__(self, *, timeout=10):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        self.timeout = timeout
        self._namespaces = {}
        self._actions = {}

    def namespace(self, name: str, *, chat_id, thread_id):
        if (not isinstance(name, str) or not _KEY.fullmatch(name)
                or name in _CORE or name.startswith(("mb", "mx"))):
            raise ValueError("Invalid or reserved namespace")
        if chat_id is None or not str(chat_id).strip():
            raise ValueError("An explicit chat_id is required")
        scope = (str(chat_id), str(thread_id) if thread_id is not None else None)
        if name in self._namespaces:
            namespace = self._namespaces[name]
            if (namespace.chat_id, namespace.thread_id) != scope:
                raise ValueError("Namespace already has a different scope")
            return namespace
        namespace = Namespace(self, name, *scope)
        self._namespaces[name] = namespace
        return namespace

    @property
    def keys(self):
        return tuple(self._actions)

    def resolve(self, data):
        if not isinstance(data, str):
            return None
        parts = data.split(":", 2)
        if len(parts) != 3 or (parts[0], parts[1]) not in self._actions:
            return None
        namespace, handler = self._actions[tuple(parts[:2])]
        return namespace, handler, parts[1], parts[2]

    @property
    def pattern(self):
        return r"^(?:" + "|".join(re.escape(f"{ns}:{action}:") for ns, action in self.keys) + ")"
