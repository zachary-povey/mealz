"""Plan next week's dinners and write them to content/meal_plans.

Usage (from the automations directory):

    python -m meal_planner [--week-start YYYY-MM-DD] [--portions N] [--seed N] [--dry-run]
"""

import argparse
import random
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from meal_planner.meal_plans import (
    DAYS_IN_WEEK,
    PlannedDinner,
    dinner_on,
    upcoming_monday,
    write_plan,
)
from meal_planner.nursery import NurseryMenu
from meal_planner.paths import (
    MEAL_PLANS_DIR,
    NURSERY_MENU_PATH,
    RECIPES_DIR,
    SIMILARITY_CACHE_PATH,
)
from meal_planner.planner import DinnerSlot, PlanningContext, plan_dinners
from meal_planner.recipes import load_recipes_with_tag
from meal_planner.similarity import LunchSimilarity, OpenAISimilarityJudge

TIMEZONE = ZoneInfo("Europe/Madrid")
DINNER_TAG = "dinner"
DEFAULT_PORTIONS = 4


def _monday(value: str) -> date:
    day = date.fromisoformat(value)
    if day.weekday() != 0:
        raise argparse.ArgumentTypeError(f"{value} is not a Monday")
    return day


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--week-start",
        type=_monday,
        help="Monday to plan the week from (default: the upcoming Monday)",
    )
    parser.add_argument(
        "--portions",
        type=int,
        default=DEFAULT_PORTIONS,
        help=f"portions to cook of each dinner (default: {DEFAULT_PORTIONS})",
    )
    parser.add_argument("--seed", type=int, help="random seed, for a reproducible plan")
    parser.add_argument(
        "--dry-run", action="store_true", help="print the plan without writing it"
    )
    return parser.parse_args()


def main() -> None:
    """Plan a week of dinners and write the meal plan."""
    args = parse_args()
    now = datetime.now(TIMEZONE)
    week_start: date = args.week_start or upcoming_monday(now.date())

    menu = NurseryMenu.load(NURSERY_MENU_PATH)
    recipes = load_recipes_with_tag(RECIPES_DIR, DINNER_TAG)
    if not recipes:
        raise RuntimeError(f"No recipes in {RECIPES_DIR} are tagged '{DINNER_TAG}'")
    titles = {recipe.slug: recipe.title for recipe in recipes}

    similarity = LunchSimilarity(
        SIMILARITY_CACHE_PATH, judge=OpenAISimilarityJudge.from_env()
    )
    similar_lunch_dishes = similarity.resolve(recipes, menu.dishes)

    days = [week_start + timedelta(days=offset) for offset in range(DAYS_IN_WEEK)]
    context = PlanningContext(
        slots=tuple(DinnerSlot(day, menu.lunch_on(day)) for day in days),
        similar_lunch_dishes=similar_lunch_dishes,
        previous_dinner=dinner_on(MEAL_PLANS_DIR, week_start - timedelta(days=1)),
    )
    plan = plan_dinners(context, list(titles), random.Random(args.seed))
    dinners = [
        PlannedDinner(slot.day, recipe, slot.nursery_lunch)
        for slot, recipe in zip(context.slots, plan.dinners)
    ]

    print(
        f"Dinners for the week of {week_start} (nursery menu week {menu.rotation_week(week_start)}):"
    )
    for dinner in dinners:
        lunch = " · ".join(dinner.nursery_lunch) or "no nursery"
        print(f"  {dinner.day:%a}: {titles[dinner.recipe]}  [lunch: {lunch}]")
    for description, count in plan.rule_violations.items():
        print(
            f"  Couldn't avoid {description} ({count}x) with the {len(recipes)} dinner recipes available"
        )

    if args.dry_run:
        return
    path, replaced = write_plan(
        MEAL_PLANS_DIR,
        week_start,
        dinners,
        portions=args.portions,
        relaxed_rules=plan.rule_violations,
        rotation_week=menu.rotation_week(week_start),
        generated_at=now,
    )
    for old in replaced:
        print(f"Removed {old}, which was an earlier plan for the same week")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
