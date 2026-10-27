import os
import stat
import sys

import pytest

from job_search.config import Settings
from job_search.repositories.secret_store import SecretStore
from job_search.services.openai_key import OpenAIKeyError, OpenAIKeyService, hint, with_saved_key

KEY = "sk-proj-abcdefghijklmnopqrstuvwxyz0123456789"


def test_secrets_are_encrypted_and_private(tmp_path):
    store = SecretStore(tmp_path, app_secret="")
    store.set("openai_api_key", KEY)
    assert store.get("openai_api_key") == KEY
    assert KEY not in (tmp_path / "secrets.json").read_text()  # never in plain text on disk
    if sys.platform != "win32":
        for name in ("secrets.json", "secret.key"):
            assert stat.S_IMODE(os.stat(tmp_path / name).st_mode) == 0o600  # only you can read them
    store.delete("openai_api_key")
    assert store.get("openai_api_key") is None


def test_app_secret_is_the_key_and_a_wrong_one_reads_nothing(tmp_path):
    SecretStore(tmp_path, app_secret="first secret").set("k", KEY)
    assert not (tmp_path / "secret.key").exists()  # APP_SECRET used, no key file written
    assert SecretStore(tmp_path, app_secret="first secret").get("k") == KEY
    assert SecretStore(tmp_path, app_secret="another secret").get("k") is None
    (tmp_path / "secrets.json").write_text("not json")
    assert SecretStore(tmp_path, app_secret="first secret").get("k") is None


def test_saved_key_wins_over_env_and_is_checked_first(tmp_path):
    checked = []
    keys = OpenAIKeyService(SecretStore(tmp_path, app_secret="s"), "sk-env-key-0000000000000000000000000", checked.append)
    assert keys.status() == {"source": "env", "hint": "sk-…0000"}
    for bad in ("", "hello", "sk-short", f"{KEY} extra", None, 42):
        with pytest.raises(OpenAIKeyError):
            keys.save(bad)
    assert checked == []  # bad shapes never reach OpenAI
    assert keys.save(f"  {KEY}\n") == {"source": "settings", "hint": hint(KEY)}
    assert checked == [KEY] and keys.current() == KEY

    settings = with_saved_key(Settings(openai_api_key="sk-env", history_path=tmp_path / "h.sqlite3"), keys)
    assert settings.api_key() == KEY and KEY not in repr(settings) and "sk-env" not in repr(settings)
    keys.remove()
    assert settings.api_key() == "sk-env"  # back to .env, no restart needed


def test_a_refused_key_is_not_saved(tmp_path):
    def refuse(key):
        raise OpenAIKeyError("OpenAI didn't accept this key.")

    keys = OpenAIKeyService(SecretStore(tmp_path, app_secret="s"), None, refuse)
    with pytest.raises(OpenAIKeyError, match="didn't accept"):
        keys.save(KEY)
    assert keys.status() == {"source": None, "hint": None}
