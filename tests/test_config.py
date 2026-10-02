from pathlib import Path

import pytest

import job_search.config as config
from job_search.cli import build_options, build_parser
from job_search.config import Settings, load_settings

ENV_NAMES = ["RESULTS_LINKEDIN", "RESULTS_NAUKRI", "EXPERIENCE", "ONLY_NEW", "HISTORY_DB", "OPENAI_API_KEY", "OPENAI_MODEL", "RESUME", "LOCATION", "KEYWORDS", "SITES", "RESULTS", "HOURS", "TOP", "MAX_PAGES"]


@pytest.fixture
def env(monkeypatch):
    """A clean environment: ignore any real .env on this machine."""
    monkeypatch.setattr(config, "load_dotenv", lambda *args, **kwargs: None)
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_defaults_when_nothing_is_set(env):
    settings = load_settings()
    assert settings.resume is None
    assert settings.keywords == []
    assert (settings.results, settings.hours, settings.top, settings.max_pages) == (10, 24, 40, 3)


def test_reads_search_settings(env):
    env.setenv("RESUME", "C:/Users/me/resume.pdf")
    env.setenv("LOCATION", "Bengaluru, Remote")
    env.setenv("KEYWORDS", "Python Developer, SDET ,")
    env.setenv("SITES", "LinkedIn")
    env.setenv("RESULTS", "20")
    env.setenv("HOURS", "12")

    settings = load_settings()

    assert settings.resume == Path("C:/Users/me/resume.pdf")
    assert settings.locations == ["Bengaluru", "Remote"]
    assert settings.keywords == ["Python Developer", "SDET"]
    assert settings.sites == ["linkedin"]
    assert (settings.results, settings.hours) == (20, 12)


def test_empty_and_quoted_values(env):
    env.setenv("LOCATION", "")
    env.setenv("RESUME", '"My Resume.pdf"')
    settings = load_settings()
    assert settings.locations == []
    assert settings.resume == Path("My Resume.pdf")


@pytest.mark.parametrize("value", ["ten", "0", "-5"])
def test_bad_numbers_give_clear_error(env, value):
    env.setenv("RESULTS", value)
    with pytest.raises(ValueError, match="RESULTS in .env"):
        load_settings()


def options_for(argv, **settings):
    return build_options(build_parser().parse_args(argv), Settings(openai_api_key="key", **settings))


def test_env_values_used_when_no_options_passed():
    options = options_for([], resume=Path("cv.pdf"), locations=["Pune"], keywords=["SDET"], results=20, top=15)

    assert options.resume_path == Path("cv.pdf")
    assert options.locations == ["Pune"]
    assert options.keywords == ["SDET"]
    assert options.results == 20
    assert options.top_n == 15
    assert options.sites == ["linkedin", "naukri", "indeed"]


def test_command_line_wins_over_env():
    options = options_for(
        ["--resume", "other.pdf", "--results", "5", "--location", "Delhi", "Remote", "--keywords", "QA Engineer"],
        resume=Path("cv.pdf"),
        locations=["Pune"],
        keywords=["SDET"],
        results=20,
    )
    assert options.resume_path == Path("other.pdf")
    assert options.results == 5
    assert options.locations == ["Delhi", "Remote"]
    assert options.keywords == ["QA Engineer"]


def test_missing_resume_explains_both_ways():
    with pytest.raises(ValueError, match="RESUME=") as error:
        options_for([])
    assert "--resume" in str(error.value)


def test_unknown_site_in_env():
    with pytest.raises(ValueError, match="unknown site"):
        options_for([], resume=Path("cv.pdf"), sites=["monster"])


def test_no_llm_accepts_keywords_from_env():
    assert options_for(["--no-llm"], resume=Path("cv.pdf"), keywords=["SDET"]).use_llm is False
    with pytest.raises(ValueError, match="--no-llm needs keywords"):
        options_for(["--no-llm"], resume=Path("cv.pdf"))


def test_zero_results_rejected():
    with pytest.raises(ValueError, match="--results must be at least 1"):
        options_for(["--results", "0"], resume=Path("cv.pdf"))


def test_reads_results_per_site(env):
    env.setenv("RESULTS_LINKEDIN", "20")
    env.setenv("RESULTS_NAUKRI", "12")
    assert load_settings().results_per_site == {"linkedin": 20, "naukri": 12}


def test_results_per_site_from_env_and_command_line():
    env_counts = {"linkedin": 20, "naukri": 12}
    options = options_for([], resume=Path("cv.pdf"), results_per_site=env_counts)
    assert (options.results, options.results_per_site) == (10, env_counts)

    # SITE=N on the command line changes just that site.
    options = options_for(["--results", "linkedin=5"], resume=Path("cv.pdf"), results_per_site=env_counts)
    assert options.results_per_site == {"linkedin": 5, "naukri": 12}

    # A plain number applies to every site for this run.
    options = options_for(["--results", "3"], resume=Path("cv.pdf"), results_per_site=env_counts)
    assert (options.results, options.results_per_site) == (3, {})


def test_bad_results_values():
    with pytest.raises(ValueError, match="SITE=NUMBER"):
        options_for(["--results", "linkedin=many"], resume=Path("cv.pdf"))
    with pytest.raises(ValueError, match="unknown site"):
        options_for(["--results", "monster=5"], resume=Path("cv.pdf"))


def test_experience_and_only_new_from_env(env):
    env.setenv("EXPERIENCE", "1-2")
    env.setenv("ONLY_NEW", "yes")
    settings = load_settings()
    assert settings.experience == (1, 2)
    assert settings.only_new is True


@pytest.mark.parametrize(("name", "value"), [("EXPERIENCE", "junior"), ("ONLY_NEW", "maybe")])
def test_bad_experience_or_only_new_in_env(env, name, value):
    env.setenv(name, value)
    with pytest.raises(ValueError, match=f"{name} in .env"):
        load_settings()


def test_experience_and_only_new_options():
    options = options_for(["--experience", "2 to 4", "--only-new"], resume=Path("cv.pdf"), experience=(0, 1))
    assert options.experience == (2, 4)
    assert options.only_new is True
    options = options_for(["--no-only-new"], resume=Path("cv.pdf"), experience=(0, 1), only_new=True)
    assert (options.experience, options.only_new) == ((0, 1), False)
    with pytest.raises(ValueError, match="experience must look like"):
        options_for(["--experience", "senior"], resume=Path("cv.pdf"))
