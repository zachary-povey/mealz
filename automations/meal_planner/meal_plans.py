from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import frontmatter
import yaml

DAYS_IN_WEEK = 7


@dataclass(frozen=True)
class PlannedDinner:
    """One day's dinner in a meal plan.

    Attributes:
        day: The date of the dinner.
        recipe: Slug of the recipe being cooked.
        nursery_lunch: The dishes eaten at nursery lunch that day, empty if there is no nursery.
    """

    day: date
    recipe: str
    nursery_lunch: tuple[str, ...]


def upcoming_monday(today: date) -> date:
    """Return the first Monday strictly after `today`."""
    return today + timedelta(days=DAYS_IN_WEEK - today.weekday())


def _as_date(value: object, source: Path, key: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValueError(f"Meal plan {source} has an invalid {key}: {value!r}")


def _load_plans(plans_dir: Path) -> list[tuple[Path, frontmatter.Post]]:
    return [
        (path, frontmatter.load(path))
        for path in sorted(plans_dir.glob("*.md"))
        if not path.name.startswith("_")
    ]


def plans_starting_in_week(plans_dir: Path, week_start: date) -> list[Path]:
    """Return the meal plan files whose plan starts in the week beginning `week_start`.

    Raises:
        ValueError: If a meal plan has a missing or invalid `plan_start`.
    """
    week_end = week_start + timedelta(days=DAYS_IN_WEEK - 1)
    return [
        path
        for path, post in _load_plans(plans_dir)
        if week_start
        <= _as_date(post.metadata.get("plan_start"), path, "plan_start")
        <= week_end
    ]


def dinner_on(plans_dir: Path, day: date) -> str | None:
    """Return the slug of the recipe planned for dinner on `day`, if any plan schedules one."""
    for path, post in _load_plans(plans_dir):
        for dinner in post.metadata.get("dinners") or []:
            if _as_date(dinner.get("date"), path, "dinner date") == day:
                return dinner["recipe"]
    return None


def write_plan(
    plans_dir: Path,
    week_start: date,
    dinners: Sequence[PlannedDinner],
    portions: int,
    relaxed_rules: dict[str, int],
    rotation_week: int,
    generated_at: datetime,
) -> tuple[Path, list[Path]]:
    """Write a week's dinner plan, replacing any plans already made for that week.

    Args:
        plans_dir: Directory holding the meal plan markdown files.
        week_start: The Monday the plan starts on.
        dinners: The dinner for each day of the week, in order.
        portions: Number of portions to cook of each dinner.
        relaxed_rules: Planning rules that couldn't be met, and how many times each was broken.
        rotation_week: The nursery menu rotation week the plan falls in.
        generated_at: When the plan was made (timezone aware).

    Returns:
        The path of the new plan, and the paths of any other plans for that week that were removed.

    Raises:
        ValueError: If `week_start` isn't a Monday or `dinners` doesn't cover exactly that week.
    """
    if week_start.weekday() != 0:
        raise ValueError(f"Meal plans must start on a Monday, {week_start} is not one")
    expected_days = [
        week_start + timedelta(days=offset) for offset in range(DAYS_IN_WEEK)
    ]
    if [dinner.day for dinner in dinners] != expected_days:
        raise ValueError(
            f"Dinners must cover each day from {week_start} to {expected_days[-1]} in order"
        )
    if generated_at.tzinfo is None:
        raise ValueError("generated_at must be timezone aware")

    path = plans_dir / f"{week_start.isoformat()}.md"
    replaced = [
        old for old in plans_starting_in_week(plans_dir, week_start) if old != path
    ]
    for old in replaced:
        old.unlink()

    metadata = {
        "title": f"Week of {week_start.strftime('%A')} {week_start.day} {week_start.strftime('%B %Y')}",
        "date": generated_at.isoformat(timespec="seconds"),
        "plan_start": week_start,
        "plan_end": expected_days[-1],
        "nursery_rotation_week": rotation_week,
        "portions": portions,
        "relaxed_rules": [
            f"{description} ({count}x)" for description, count in relaxed_rules.items()
        ],
        "dinners": [
            {
                "date": dinner.day,
                "recipe": dinner.recipe,
                "nursery_lunch": list(dinner.nursery_lunch),
            }
            for dinner in dinners
        ],
    }
    with open(path, "w") as fp:
        fp.write("---\n")
        yaml.safe_dump(metadata, fp, allow_unicode=True, sort_keys=False)
        fp.write("---\n")
    return path, replaced
