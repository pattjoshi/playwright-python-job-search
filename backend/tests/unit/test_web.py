import pytest

from job_search.schemas.serializers import suggest_experience


@pytest.mark.parametrize(("years", "expected"), [(4, [3, 5]), (0.5, [0, 2]), (0, [0, 1]), (None, None)])
def test_suggest_experience(years, expected):
    assert suggest_experience(years) == expected
