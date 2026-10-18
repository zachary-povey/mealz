import random
import time
from datetime import date, timedelta

import pytest

from meal_planner.planner import DinnerSlot, PlanningContext, plan_dinners

MONDAY = date(2026, 10, 19)
CLASH = "dinner the same as or very similar to that day's nursery lunch"
CONSECUTIVE = "the same dinner two days in a row"
REPEAT = "the same dinner more than once in the week"


def week(lunches: dict[int, tuple[str, ...]] | None = None) -> tuple[DinnerSlot, ...]:
    lunches = lunches or {}
    return tuple(
        DinnerSlot(MONDAY + timedelta(days=offset), lunches.get(offset, ()))
        for offset in range(7)
    )


def test_meets_every_rule_when_possible() -> None:
    context = PlanningContext(
        slots=week({0: ("pasta boloñesa",), 1: ("tortilla de patatas",)}),
        similar_lunch_dishes={
            "bolognese": frozenset({"pasta boloñesa"}),
            "tortilla": frozenset({"tortilla de patatas"}),
        },
    )
    recipes = [
        "bolognese",
        "tortilla",
        "salmon",
        "pizza",
        "crepes",
        "soup",
        "curry",
        "pie",
    ]

    for seed in range(20):
        plan = plan_dinners(context, recipes, random.Random(seed))
        assert plan.rule_violations == {}
        assert len(set(plan.dinners)) == 7
        assert plan.dinners[0] != "bolognese"
        assert plan.dinners[1] != "tortilla"


def test_varies_between_runs() -> None:
    context = PlanningContext(slots=week())
    recipes = [f"recipe_{n}" for n in range(10)]

    plans = {
        plan_dinners(context, recipes, random.Random(seed)).dinners
        for seed in range(10)
    }

    assert len(plans) > 1


def test_relaxes_weekly_repeats_only_as_far_as_needed() -> None:
    plan = plan_dinners(
        PlanningContext(slots=week()), ["a", "b", "c"], random.Random(0)
    )

    assert plan.rule_violations == {REPEAT: 4}
    assert set(plan.dinners) == {"a", "b", "c"}
    assert all(
        today != tomorrow for today, tomorrow in zip(plan.dinners, plan.dinners[1:])
    )


def test_avoids_repeating_the_previous_days_dinner_across_weeks() -> None:
    context = PlanningContext(slots=week(), previous_dinner="a")

    for seed in range(20):
        plan = plan_dinners(context, ["a", "b"], random.Random(seed))
        assert plan.dinners == ("b", "a", "b", "a", "b", "a", "b")


def test_nursery_clash_outranks_consecutive_repeats() -> None:
    # Only "a" avoids the lunch on Tuesday and Wednesday, so it has to be served two days running.
    context = PlanningContext(
        slots=week({1: ("x",), 2: ("x",)}),
        similar_lunch_dishes={"b": frozenset({"x"}), "c": frozenset({"x"})},
    )

    plan = plan_dinners(context, ["a", "b", "c"], random.Random(0))

    assert plan.dinners[1:3] == ("a", "a")
    assert CLASH not in plan.rule_violations
    assert plan.rule_violations[CONSECUTIVE] == 1


def test_consecutive_repeats_outrank_weekly_repeats() -> None:
    # Tuesday must be "b" and Wednesday "a"; on Monday "c" would avoid a weekly repeat but
    # follows last night's "c", so "a" is the better choice.
    context = PlanningContext(
        slots=week({0: ("m",), 1: ("t",), 2: ("w",)})[:3],
        similar_lunch_dishes={
            "a": frozenset({"t"}),
            "b": frozenset({"m", "w"}),
            "c": frozenset({"t", "w"}),
        },
        previous_dinner="c",
    )

    for seed in range(10):
        plan = plan_dinners(context, ["a", "b", "c"], random.Random(seed))
        assert plan.dinners == ("a", "b", "a")
        assert plan.rule_violations == {REPEAT: 1}


def test_breaks_the_nursery_rule_only_on_days_with_no_alternative() -> None:
    context = PlanningContext(
        slots=week({0: ("x",), 3: ("y",)}),
        similar_lunch_dishes={"a": frozenset({"x", "y"}), "b": frozenset({"x"})},
    )

    plan = plan_dinners(context, ["a", "b"], random.Random(0))

    assert plan.rule_violations[CLASH] == 1
    assert plan.dinners[3] == "b"


def test_single_recipe_fills_the_week() -> None:
    plan = plan_dinners(PlanningContext(slots=week()), ["a"], random.Random(0))

    assert plan.dinners == ("a",) * 7
    assert plan.rule_violations == {CONSECUTIVE: 6, REPEAT: 6}


def test_rejects_empty_recipe_list() -> None:
    with pytest.raises(ValueError, match="no recipes"):
        plan_dinners(PlanningContext(slots=week()), [], random.Random(0))


@pytest.mark.parametrize("n_recipes", [6, 8, 12, 40])
def test_is_fast_with_heavy_clashes(n_recipes: int) -> None:
    rng = random.Random(n_recipes)
    dishes = [f"dish_{n}" for n in range(10)]
    lunches = {offset: tuple(rng.sample(dishes, 2)) for offset in range(5)}
    similar = {f"r{n}": frozenset(rng.sample(dishes, 6)) for n in range(n_recipes)}
    context = PlanningContext(
        slots=week(lunches), similar_lunch_dishes=similar, previous_dinner="r0"
    )

    started = time.monotonic()
    plan_dinners(context, list(similar), random.Random(0))

    assert time.monotonic() - started < 2
