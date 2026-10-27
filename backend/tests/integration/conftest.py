import pytest
from fastapi.testclient import TestClient

from job_search.api.app import create_app
from job_search.config import Settings
from tests.auth_helpers import signed_in
from tests.integration.web_support import PROFILE, FakeRunner, FakeScheduler


@pytest.fixture
def make_client(tmp_path):
    def make(runner=None, api_key="key", analyzer=None, scheduler=None, answer_ai=None, key_checker=None, **settings):
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)
        runner = runner or FakeRunner(output_dir)
        app = create_app(
            Settings(openai_api_key=api_key, history_path=tmp_path / "history.sqlite3", **settings),
            output_dir=output_dir,
            upload_dir=tmp_path / "uploads",
            runner=runner,
            analyzer=analyzer or (lambda path: PROFILE),
            system_scheduler=scheduler or FakeScheduler(),
            frontend_dir=tmp_path / "frontend",
            answer_ai=answer_ai or (lambda: None),  # tests never call OpenAI
            key_checker=key_checker or (lambda key: None),  # ...not even to check a key
        )
        return signed_in(TestClient(app)), runner

    return make
