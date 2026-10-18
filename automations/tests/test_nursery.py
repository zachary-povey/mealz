from datetime import date
from pathlib import Path

import pytest

from meal_planner.nursery import NurseryMenu
from meal_planner.paths import NURSERY_MENU_PATH


@pytest.fixture
def menu() -> NurseryMenu:
    return NurseryMenu.load(NURSERY_MENU_PATH)


@pytest.mark.parametrize(
    "day, expected_week",
    [
        (date(2026, 9, 14), 2),
        (date(2026, 9, 20), 2),
        (date(2026, 9, 7), 1),
        (date(2026, 8, 31), 4),
        (date(2026, 10, 5), 1),
        (date(2026, 10, 21), 3),
        (date(2026, 11, 2), 1),
    ],
)
def test_rotation_week(menu: NurseryMenu, day: date, expected_week: int) -> None:
    assert menu.rotation_week(day) == expected_week


def test_lunch_on_weekday(menu: NurseryMenu) -> None:
    assert menu.lunch_on(date(2026, 10, 9)) == (
        "ensalada variada (pescado)",
        "pasta boloñesa",
    )


def test_no_lunch_at_weekends(menu: NurseryMenu) -> None:
    assert menu.lunch_on(date(2026, 10, 10)) == ()
    assert menu.lunch_on(date(2026, 10, 11)) == ()


def test_dishes_are_unique(menu: NurseryMenu) -> None:
    assert len(menu.dishes) == len(set(menu.dishes))
    assert "pasta boloñesa" in menu.dishes


def test_rejects_anchor_that_is_not_a_monday(tmp_path: Path) -> None:
    path = tmp_path / "menu.yaml"
    path.write_text(
        "anchor: {week_start: 2026-09-15, rotation_week: 1}\n"
        "weeks:\n  1: {monday: [a], tuesday: [a], wednesday: [a], thursday: [a], friday: [a]}\n"
    )
    with pytest.raises(ValueError, match="not a Monday"):
        NurseryMenu.load(path)


def test_rejects_week_with_missing_day(tmp_path: Path) -> None:
    path = tmp_path / "menu.yaml"
    path.write_text(
        "anchor: {week_start: 2026-09-14, rotation_week: 1}\n"
        "weeks:\n  1: {monday: [a], tuesday: [a], wednesday: [a], thursday: [a]}\n"
    )
    with pytest.raises(ValueError, match="exactly"):
        NurseryMenu.load(path)
