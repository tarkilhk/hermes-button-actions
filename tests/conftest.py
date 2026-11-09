import json
from contextvars import ContextVar
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from types import ModuleType

import pytest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def hermes_constants_stub(monkeypatch, isolated_home):
    """Unit-test double only; real framework tests use hermes_source instead."""
    module = ModuleType("hermes_constants")
    home = ContextVar("test_profile_home", default=isolated_home)
    module.get_hermes_home = lambda: Path(home.get())
    module.set_hermes_home_override = home.set
    module.reset_hermes_home_override = home.reset
    monkeypatch.setitem(sys.modules, "hermes_constants", module)
    return module


@pytest.fixture
def hermes_source(monkeypatch):
    source = os.environ.get("HERMES_SOURCE")
    if not source or not (Path(source) / "hermes_constants.py").is_file():
        pytest.skip("Set HERMES_SOURCE to a Hermes source checkout for framework integration tests")
    monkeypatch.syspath_prepend(str(Path(source).resolve()))
    try:
        # Probe optional imports before running the test; API/behavior errors still fail.
        from gateway.config import PlatformConfig
        from hermes_cli.plugins import get_plugin_manager
        from plugins.platforms.telegram.adapter import TelegramAdapter
    except ModuleNotFoundError as exc:
        pytest.skip(f"Optional Hermes integration dependency unavailable: {exc.name}; install integration-test extras")


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "empty-bundled").mkdir()
    (home / "config.yaml").write_text("plugins:\n  enabled: []\n  isolation: in_process\n")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(home / "empty-bundled"))
    monkeypatch.setenv("HERMES_ENABLE_PROJECT_PLUGINS", "0")
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    def no_network(*args, **kwargs):
        raise AssertionError("Network forbidden in tests")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket.socket, "connect_ex", no_network)
    return home


@pytest.fixture
def synthetic_inbox(tmp_path, isolated_home):
    # Unmodified CLI source snapshot, without the real project's .env or database.
    source_value = os.environ.get("REMINDER_INBOX_SOURCE")
    if not source_value or not (Path(source_value) / "reminder_inbox" / "schema.sql").is_file():
        pytest.skip("Set REMINDER_INBOX_SOURCE to a Reminder Inbox source checkout for CLI integration tests")
    if importlib.util.find_spec("requests") is None:
        pytest.skip("Optional Reminder Inbox dependency unavailable: requests; install integration-test extras")
    source = Path(source_value).resolve()
    cwd = tmp_path / "synthetic-inbox"
    package = cwd / "reminder_inbox"
    package.mkdir(parents=True)
    for path in (source / "reminder_inbox").glob("*.py"):
        shutil.copyfile(path, package / path.name)
    shutil.copyfile(source / "reminder_inbox" / "schema.sql", package / "schema.sql")
    # Loaded by every synthetic CLI child, including children spawned by the provider.
    # No .env, data, or credentials are copied, and even accidental network use fails.
    (cwd / "sitecustomize.py").write_text(
        'import socket\n'
        'def no_network(*args, **kwargs):\n'
        '    raise AssertionError("Network forbidden in synthetic CLI tests")\n'
        'socket.socket.connect = no_network\n'
        'socket.socket.connect_ex = no_network\n')
    executable = cwd / "reminder-inbox"
    executable.write_text(f"#!{sys.executable}\nimport sitecustomize\nfrom reminder_inbox.cli import main\nmain()\n")
    executable.chmod(0o700)
    options = dict(executable=str(executable), cwd=str(cwd), db_path=str(cwd / "synthetic.sqlite3"),
                   chat_id="-100123", thread_id="42")
    env = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "HERMES_HOME": str(isolated_home),
           "REMINDER_INBOX_DB_PATH": options["db_path"], "TMPDIR": os.environ["TMPDIR"]}

    def cli(*args):
        completed = subprocess.run([str(executable), *args, "--json"], cwd=cwd, env=env,
                                   capture_output=True, text=True, check=True)
        return json.loads(completed.stdout)["data"]

    source_item = cli("source", "add", "--source", "telegram", "--source-id", "synthetic-message",
                      "--chat-id", options["chat_id"], "--thread-id", options["thread_id"], "--text", "Synthetic event")

    def draft(**scope):
        event = {"title": "Synthetic only", "category": "generic", "timezone": "UTC",
                 "start_time": "2099-12-01T12:00:00+00:00", "confidence": 0.9}
        return cli("draft", "create", "--source-item-id", source_item["id"], "--event-json", json.dumps(event),
                   "--chat-id", scope.get("chat_id", options["chat_id"]),
                   "--thread-id", scope.get("thread_id", options["thread_id"]))

    return options, cli, draft
