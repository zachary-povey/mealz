# Content and data formats

Every file the site and planner read lives in `content/` or `data/`. Hugo publishes all of it, so it is public.

## Recipes: `content/recipes/<slug>.md`

The file name without `.md` is the recipe's **slug**. Meal plans and the similarity cache refer to recipes by slug. If you rename a recipe file, update any meal plans that reference it, or the site build will fail (on purpose).

```yaml
---
title: Macaroni Cheese              # required
date: '2026-10-18'
tags:                                # list; "dinner" makes it eligible for the planner
- dinner
original_url: https://example.com/…  # optional; shown as an "Original Recipe" link
draft: true                          # optional; drafts are skipped by Hugo and the planner
ingredients:
-   name: wholewheat macaroni        # free text; must match the ingredient_mention names below
    quantity_per_serving:
        units: g                     # free text or null/missing (e.g. "2 eggs" has no unit)
        value: 75                    # per ONE serving; 0 shows just the name (e.g. salt to taste)
-   name: cheddar
    quantity_per_serving:
        units: g
        value: 40
---
1. Cook the {{< ingredient_mention name="wholewheat macaroni" fraction="1.0" >}} as per the packet.
2. Stir in {{< ingredient_mention name="cheddar" fraction="0.75" >}} …
3. Scatter over the remaining {{< ingredient_mention name="cheddar" fraction="0.25" >}} …
```

- **Quantities are per serving.** The recipe page multiplies them by the serving count chosen in the page, which comes from the `?portions=N` URL parameter and defaults to 2.
- **`ingredient_mention` shortcode** (`layouts/shortcodes/ingredient_mention.html`): the recipe page's JavaScript replaces each mention with the full scaled quantity, e.g. "300 g wholewheat macaroni". `fraction` is the share of the ingredient used at that step. `name` must exactly match an ingredient `name`, because the JavaScript finds the mention via a CSS class made from the name with spaces replaced by underscores.
- **Instructions** are a numbered markdown list. Older recipes use `-` bullets, and some are in Spanish.
- **Units and names are not normalised.** Recipes mix metric, imperial and Spanish or English names ("olive oil" vs "aceite de oliva"). The shopping list only combines lines whose name and unit match exactly. The vision's goal is metric everywhere.
- **Tags**: `dinner` is the only tag the code uses. Other tags in use include `lunch`, `breakfast` and `baby`. Both `tags: [dinner]` and the block-list form are fine; matching ignores case.
- **New recipes** usually come from `automations/import_recipe.py` (see [development.md](development.md#other-automation-scripts)). It writes `tags: []`, so add `dinner` by hand if the recipe should be planned.

## Meal plans: `content/meal_plans/<YYYY-MM-DD>.md`

There are two formats. The templates (`layouts/partials/meal_plan_entries.html`) handle both.

### Day-by-day format (written by the planner)

The file is named after the Monday the plan starts on.

```yaml
---
title: Week of Monday 19 October 2026
date: '2026-10-18T13:44:05+02:00'   # when it was generated
plan_start: 2026-10-19               # Monday
plan_end: 2026-10-25                 # Sunday
nursery_rotation_week: 3
portions: 4                          # portions of each dinner (recipe links and shopping list use it)
relaxed_rules: []                    # rules the planner couldn't meet, e.g. "the same dinner more than once in the week (2x)"
dinners:                             # exactly 7 entries, Monday to Sunday
- date: 2026-10-19
  recipe: sausages_and_mash          # recipe slug
  nursery_lunch:                     # that day's nursery lunch dishes; [] at weekends
  - arroz guisado con carne
  - tortilla de melva con ensalada
…
---
```

You can edit a generated plan by hand, e.g. to swap a dinner. Keep `recipe` a valid slug. The planner replaces the whole file if the week is re-planned.

### Legacy format (plans before October 2026)

```yaml
---
title: Meal Plan for 2025-06-07 -> 2025-06-13
plan_start: 2025-06-07
plan_end: 2025-06-13
meals:              # recipe slug: portions, no days (lunches, dinners, batch cooking all mixed)
    bolognese: 8
    waldorf_salad: 4
---
```

`archetypes/meal_plans.md` (`hugo new meal_plans/<date>.md`) still produces this format. The planner ignores legacy plans, except that it reads `plan_start` from every plan to find ones to replace, so every plan must have a valid `plan_start`.

## Nursery menu: `data/nursery_menu.yaml`

```yaml
anchor:
  week_start: 2026-09-14   # a Monday…
  rotation_week: 2         # …that is week 2 of the rotation
weeks:
  1:
    monday: [crema de calabacín, lomo guisado con tomate]   # usually a first and second course
    tuesday: […]
    …                       # exactly monday–friday; no nursery lunch at weekends
  2: …
```

- The rotation repeats forever from the anchor: `week = (rotation_week - 1 + weeks_since_anchor) mod 4 + 1`.
- **Re-anchoring:** if the nursery skips or repeats a week (holidays, etc.), set `anchor.week_start` to a recent Monday and `rotation_week` to the week the nursery is actually serving then.
- Changing dish names makes the planner re-judge every recipe on its next run, because the menu is part of each judgement's fingerprint.
- Keep the nursery's name and location out of this file: the repo is public.

## Similarity cache: `data/lunch_similarity.yaml`

This file is generated by the planner and committed. For each recipe tagged `dinner`, it lists the nursery lunch dishes the recipe is "the same as or very similar to":

```yaml
mild_chicken_curry_with_rice:
  fingerprint: 3f1c…            # hash of the recipe + menu dishes + JUDGEMENT_VERSION
  similar_lunch_dishes:
  - pollo guisado con verduras
```

- **Hand edits are respected** until the recipe, the menu or `JUDGEMENT_VERSION` changes. At that point the entry is re-judged and the edit is lost.
- Dish names must exactly match dishes in `data/nursery_menu.yaml`, otherwise the planner raises an error.
- Entries for recipes that are no longer tagged `dinner` are removed on the next run.

See [meal-planner.md](meal-planner.md#lunch-similarity) for how it is produced.
