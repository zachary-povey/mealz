from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import yaml

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")


def week_start_of(day: date) -> date:
    """Return the Monday of the week containing `day`."""
    return day - timedelta(days=day.weekday())


@dataclass(frozen=True)
class NurseryMenu:
    """The nursery's repeating multi-week lunch menu.

    Attributes:
        anchor_week_start: A Monday whose week is known to be `anchor_rotation_week` of the rotation.
        anchor_rotation_week: The rotation week (1-based) of the anchor week.
        weeks: For each rotation week, the lunch dishes served on each weekday (0 = Monday).
    """

    anchor_week_start: date
    anchor_rotation_week: int
    weeks: dict[int, dict[int, tuple[str, ...]]]

    def __post_init__(self) -> None:
        if self.anchor_week_start.weekday() != 0:
            raise ValueError(
                f"Nursery menu anchor {self.anchor_week_start} is not a Monday"
            )
        if sorted(self.weeks) != list(range(1, len(self.weeks) + 1)):
            raise ValueError(
                f"Nursery menu weeks must be numbered 1 to {len(self.weeks)}, got {sorted(self.weeks)}"
            )
        if self.anchor_rotation_week not in self.weeks:
            raise ValueError(
                f"Nursery menu anchor week {self.anchor_rotation_week} is not in the menu"
            )

    @classmethod
    def load(cls, path: Path) -> "NurseryMenu":
        """Load the nursery menu from its YAML file.

        Args:
            path: Path to the nursery menu YAML file.

        Returns:
            The parsed nursery menu.

        Raises:
            ValueError: If the file is not in the expected format.
        """
        with open(path) as fp:
            raw = yaml.safe_load(fp)

        try:
            anchor_week_start = raw["anchor"]["week_start"]
            anchor_rotation_week = int(raw["anchor"]["rotation_week"])
            raw_weeks = raw["weeks"]
        except (TypeError, KeyError) as e:
            raise ValueError(f"Nursery menu {path} is missing required key {e}") from e
        if not isinstance(anchor_week_start, date):
            raise ValueError(
                f"Nursery menu anchor week_start must be a date, got {anchor_week_start!r}"
            )

        weeks: dict[int, dict[int, tuple[str, ...]]] = {}
        for week_number, days in raw_weeks.items():
            if set(days) != set(WEEKDAYS):
                raise ValueError(
                    f"Nursery menu week {week_number} must list exactly {', '.join(WEEKDAYS)}, "
                    f"got {', '.join(days)}"
                )
            weeks[int(week_number)] = {
                WEEKDAYS.index(day_name): tuple(str(dish) for dish in dishes)
                for day_name, dishes in days.items()
            }

        return cls(
            anchor_week_start=anchor_week_start,
            anchor_rotation_week=anchor_rotation_week,
            weeks=weeks,
        )

    def rotation_week(self, day: date) -> int:
        """Return which week of the rotation (1-based) `day` falls in."""
        weeks_since_anchor = (week_start_of(day) - self.anchor_week_start).days // 7
        return (self.anchor_rotation_week - 1 + weeks_since_anchor) % len(
            self.weeks
        ) + 1

    def lunch_on(self, day: date) -> tuple[str, ...]:
        """Return the dishes served at nursery lunch on `day`, which is empty at weekends."""
        return self.weeks[self.rotation_week(day)].get(day.weekday(), ())

    @property
    def dishes(self) -> tuple[str, ...]:
        """All distinct dishes on the menu, sorted."""
        return tuple(
            sorted(
                {
                    dish
                    for days in self.weeks.values()
                    for dishes in days.values()
                    for dish in dishes
                }
            )
        )
