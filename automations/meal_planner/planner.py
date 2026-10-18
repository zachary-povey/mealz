import random
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class DinnerSlot:
    """A day that needs a dinner.

    Attributes:
        day: The date of the dinner.
        nursery_lunch: The dishes eaten at nursery lunch that day, empty if there is no nursery.
    """

    day: date
    nursery_lunch: tuple[str, ...]


@dataclass(frozen=True)
class PlanningContext:
    """Everything the planning rules need to know about the week being planned.

    Attributes:
        slots: The consecutive days to plan dinners for.
        similar_lunch_dishes: For each candidate recipe slug, the nursery lunch dishes it is the same
            as or very similar to.
        previous_dinner: Slug of the dinner eaten the day before the first slot, if known.
    """

    slots: tuple[DinnerSlot, ...]
    similar_lunch_dishes: Mapping[str, frozenset[str]] = field(default_factory=dict)
    previous_dinner: str | None = None

    def clashes_with_lunch(self, position: int, recipe: str) -> bool:
        """Whether `recipe` is too similar to the nursery lunch on the slot at `position`."""
        similar = self.similar_lunch_dishes.get(recipe, frozenset())
        return any(dish in similar for dish in self.slots[position].nursery_lunch)


class Rule(ABC):
    """A planning rule that a week of dinners should ideally never break."""

    description: str

    @abstractmethod
    def cost(
        self,
        context: PlanningContext,
        position: int,
        recipe: str,
        chosen: Sequence[str],
    ) -> int:
        """Return how many times this rule is broken by putting `recipe` in slot `position`.

        Args:
            context: The week being planned.
            position: Index of the slot being filled.
            recipe: Slug of the recipe being placed.
            chosen: Slugs already placed in slots 0 to `position - 1`.
        """

    @abstractmethod
    def remaining_lower_bound(
        self,
        context: PlanningContext,
        position: int,
        chosen: Sequence[str],
        recipes: Sequence[str],
    ) -> int:
        """Return a lower bound on how many more times the rule must be broken filling the
        slots from `position` onwards, given the recipes already chosen."""


class AvoidSimilarToNurseryLunch(Rule):
    """Don't serve a dinner that is the same as, or very similar to, that day's nursery lunch."""

    description = "dinner the same as or very similar to that day's nursery lunch"

    def cost(
        self,
        context: PlanningContext,
        position: int,
        recipe: str,
        chosen: Sequence[str],
    ) -> int:
        return int(context.clashes_with_lunch(position, recipe))

    def remaining_lower_bound(
        self,
        context: PlanningContext,
        position: int,
        chosen: Sequence[str],
        recipes: Sequence[str],
    ) -> int:
        return sum(
            all(context.clashes_with_lunch(later, recipe) for recipe in recipes)
            for later in range(position, len(context.slots))
        )


class AvoidConsecutiveRepeats(Rule):
    """Don't serve the same dinner two days running, including across the start of the week."""

    description = "the same dinner two days in a row"

    def cost(
        self,
        context: PlanningContext,
        position: int,
        recipe: str,
        chosen: Sequence[str],
    ) -> int:
        previous = chosen[position - 1] if position > 0 else context.previous_dinner
        return int(recipe == previous)

    def remaining_lower_bound(
        self,
        context: PlanningContext,
        position: int,
        chosen: Sequence[str],
        recipes: Sequence[str],
    ) -> int:
        return 0


class AvoidRepeatsWithinWeek(Rule):
    """Don't serve the same dinner more than once in the week."""

    description = "the same dinner more than once in the week"

    def cost(
        self,
        context: PlanningContext,
        position: int,
        recipe: str,
        chosen: Sequence[str],
    ) -> int:
        return int(recipe in chosen)

    def remaining_lower_bound(
        self,
        context: PlanningContext,
        position: int,
        chosen: Sequence[str],
        recipes: Sequence[str],
    ) -> int:
        unused = len(set(recipes) - set(chosen))
        return max(0, len(context.slots) - position - unused)


RULES_BY_PRIORITY: tuple[Rule, ...] = (
    AvoidSimilarToNurseryLunch(),
    AvoidConsecutiveRepeats(),
    AvoidRepeatsWithinWeek(),
)


@dataclass(frozen=True)
class DinnerPlan:
    """The chosen dinners for a run of days.

    Attributes:
        dinners: Recipe slug chosen for each slot, in slot order.
        rule_violations: How many times each rule was broken, keyed by rule description, in rule
            priority order. Only non-zero counts are included.
    """

    dinners: tuple[str, ...]
    rule_violations: dict[str, int]


def plan_dinners(
    context: PlanningContext,
    recipes: Sequence[str],
    rng: random.Random,
    rules: Sequence[Rule] = RULES_BY_PRIORITY,
) -> DinnerPlan:
    """Choose a dinner for every slot, breaking the planning rules as little as possible.

    Rules are prioritised in the order given: a plan that breaks a higher priority rule fewer times
    always wins, however many times it breaks lower priority rules. So when the rules can't all be
    met, the lowest priority rules are relaxed first, and only as far as necessary. Among equally
    good plans the choice is random.

    Args:
        context: The week being planned.
        recipes: Slugs of the recipes to choose from.
        rng: Source of randomness used to vary the plan between runs.
        rules: The rules to apply, highest priority first.

    Returns:
        The best plan found, which is optimal for the given rules.

    Raises:
        ValueError: If there are no recipes to choose from.
    """
    if not recipes:
        raise ValueError("There are no recipes to choose dinners from")
    if len(set(recipes)) != len(recipes):
        raise ValueError("Recipes to choose dinners from must be unique")

    candidates = list(recipes)
    rng.shuffle(candidates)
    n_slots = len(context.slots)

    def lower_bound(
        position: int, chosen: list[str], cost: tuple[int, ...]
    ) -> tuple[int, ...]:
        return tuple(
            spent + rule.remaining_lower_bound(context, position, chosen, candidates)
            for spent, rule in zip(cost, rules)
        )

    root_bound = lower_bound(0, [], (0,) * len(rules))
    best_cost: tuple[int, ...] | None = None
    best_plan: list[str] = []

    def search(position: int, chosen: list[str], cost: tuple[int, ...]) -> bool:
        """Depth first branch and bound search; returns True once a provably optimal plan is found."""
        nonlocal best_cost, best_plan
        if position == n_slots:
            if best_cost is None or cost < best_cost:
                best_cost, best_plan = cost, list(chosen)
            return best_cost == root_bound

        options = sorted(
            candidates,
            key=lambda recipe: tuple(
                rule.cost(context, position, recipe, chosen) for rule in rules
            ),
        )
        for recipe in options:
            step = tuple(rule.cost(context, position, recipe, chosen) for rule in rules)
            new_cost = tuple(a + b for a, b in zip(cost, step))
            chosen.append(recipe)
            if (
                best_cost is None
                or lower_bound(position + 1, chosen, new_cost) < best_cost
            ):
                if search(position + 1, chosen, new_cost):
                    return True
            chosen.pop()
        return False

    search(0, [], (0,) * len(rules))
    assert best_cost is not None

    return DinnerPlan(
        dinners=tuple(best_plan),
        rule_violations={
            rule.description: count
            for rule, count in zip(rules, best_cost)
            if count > 0
        },
    )
