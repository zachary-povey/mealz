from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import frontmatter
import pytest

from meal_planner.meal_plans import (
    PlannedDinner,
    dinner_on,
    plans_starting_in_week,
    upcoming_monday,
    write_plan,
)

MONDAY = date(2026, 10, 19)
NOW = datetime(2026, 10, 14, 7, 0, tzinfo=ZoneInfo("Europe/Madrid"))


def dinners(week_start: date, recipes: list[str] | None = None) -> list[PlannedDinner]:
    recipes = recipes or [f"recipe_{n}" for n in range(7)]
    return [
        PlannedDinner(
            week_start + timedelta(days=n), recipe, ("lunch",) if n < 5 else ()
        )
        for n, recipe in enumerate(recipes)
    ]


def write(
    plans_dir: Path, week_start: date = MONDAY, recipes: list[str] | None = None
) -> tuple[Path, list[Path]]:
    return write_plan(
        plans_dir,
        week_start,
        dinners(week_start, recipes),
        portions=4,
        relaxed_rules={"the same dinner more than once in the week": 2},
        rotation_week=3,
        generated_at=NOW,
    )


@pytest.mark.parametrize(
    "today, expected",
    [
        (date(2026, 10, 14), date(2026, 10, 19)),
        (date(2026, 10, 18), date(2026, 10, 19)),
        (date(2026, 10, 19), date(2026, 10, 26)),
        (date(2026, 10, 24), date(2026, 10, 26)),
    ],
)
def test_upcoming_monday(today: date, expected: date) -> None:
    assert upcoming_monday(today) == expected


def test_writes_plan(tmp_path: Path) -> None:
    path, replaced = write(tmp_path)

    post = frontmatter.load(path)
    assert path.name == "2026-10-19.md"
    assert replaced == []
    assert post["plan_start"] == MONDAY
    assert post["plan_end"] == date(2026, 10, 25)
    assert post["relaxed_rules"] == ["the same dinner more than once in the week (2x)"]
    assert [d["recipe"] for d in post["dinners"]] == [f"recipe_{n}" for n in range(7)]
    assert post["dinners"][5]["nursery_lunch"] == []


def test_replaces_existing_plans_for_the_week(tmp_path: Path) -> None:
    (tmp_path / "_index.md").write_text("# Meal Plans")
    (tmp_path / "2026-10-21.md").write_text(
        "---\nplan_start: 2026-10-21\nmeals: {}\n---\n"
    )
    (tmp_path / "2026-10-12.md").write_text(
        "---\nplan_start: 2026-10-12\nmeals: {}\n---\n"
    )
    _, first_replaced = write(tmp_path, recipes=["old"] * 7)

    path, replaced = write(tmp_path)

    assert first_replaced == [tmp_path / "2026-10-21.md"]
    assert replaced == []
    assert sorted(p.name for p in tmp_path.glob("*.md")) == [
        "2026-10-12.md",
        "2026-10-19.md",
        "_index.md",
    ]
    assert frontmatter.load(path)["dinners"][0]["recipe"] == "recipe_0"


def test_rejects_plans_not_starting_on_monday(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Monday"):
        write(tmp_path, week_start=date(2026, 10, 20))


def test_rejects_plan_with_invalid_start(tmp_path: Path) -> None:
    (tmp_path / "broken.md").write_text("---\ntitle: oops\n---\n")

    with pytest.raises(ValueError, match="broken.md"):
        plans_starting_in_week(tmp_path, MONDAY)


def test_dinner_on(tmp_path: Path) -> None:
    write(tmp_path, week_start=MONDAY - timedelta(days=7))

    assert dinner_on(tmp_path, MONDAY - timedelta(days=1)) == "recipe_6"
    assert dinner_on(tmp_path, MONDAY) is None
