# unit tests for quality gate checks
import pandas as pd

from src.quality.gates import (
    check_domain,
    check_not_null,
    check_referential,
    check_unique,
    score,
)


# checks null counting
def test_not_null() -> None:
    df = pd.DataFrame([{"a": 1}, {"a": None}])
    assert check_not_null(df, ["a"]) == {"a": 1}


# checks dupe counting
def test_unique() -> None:
    df = pd.DataFrame([{"a": 1}, {"a": 1}])
    assert check_unique(df, ["a"]) == {"a": 1}


# checks orphan counting
def test_referential() -> None:
    child = pd.DataFrame([{"x": 1}, {"x": 2}])
    parent = pd.DataFrame([{"y": 1}])
    assert check_referential(child, "x", parent, "y") == 1


# checks domain listing
def test_domain() -> None:
    df = pd.DataFrame([{"g": "Male"}, {"g": "X"}])
    assert check_domain(df, "g", {"Male", "Female"}) == ["X"]


# checks suite scoring
def test_score() -> None:
    pct, failed = score({"a": 0, "b": 2})
    assert pct == 50.0
    assert failed == 2
