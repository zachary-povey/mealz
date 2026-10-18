# Architecture

## Overview

Everything lives in this git repository, which is the only source of truth: there is no database or server. Content is markdown with YAML front matter. A static Hugo site is built from it and deployed to GitHub Pages. Python scripts in `automations/` create content: recipes come from an import script, and meal plans come from the dinner planner, which runs weekly in GitHub Actions.

```
                      content/recipes/*.md ◄───────── automations/import_recipe.py (run by hand)
                               │
data/nursery_menu.yaml ───┐    │ (recipes tagged "dinner")
                          ▼    ▼
              automations/meal_planner  ◄── GitHub Actions "Plan dinners"
              (Wednesdays + on demand)        (.github/workflows/plan-dinners.yaml)
                  │            │
                  │            └──► data/lunch_similarity.yaml   (OpenAI judgements, cached)
                  ▼
     content/meal_plans/<monday>.md   ── committed to main by the workflow
                  │
                  ▼
     Hugo build (layouts/, static/)   ── .github/workflows/hugo.yaml
                  │
                  ▼
     GitHub Pages: https://zachary-povey.github.io/mealz/
```

## Components

| Component | Where | What it does |
| --- | --- | --- |
| Recipe book | `content/recipes/`, `layouts/recipes/single.html` | One markdown file per recipe. The recipe page scales ingredient quantities to a chosen number of servings in the browser. |
| Meal plans | `content/meal_plans/`, `layouts/meal_plans/` | One file per week. The plans page shows weekly blocks of dinners alongside the nursery lunch. Each plan's own page is that week's shopping list. |
| Dinner planner | `automations/meal_planner/` | Picks a dinner recipe for each day of next week according to prioritised rules, then writes the plan file. See [meal-planner.md](meal-planner.md). |
| Nursery menu | `data/nursery_menu.yaml` | The son's nursery lunch menu: a fixed four-week weekday rotation, anchored to a calendar week. |
| Similarity cache | `data/lunch_similarity.yaml` | OpenAI's judgement of which nursery lunch dishes each dinner recipe is too similar to. Generated, committed, and can be hand-edited. |
| Deploy workflow | `.github/workflows/hugo.yaml` | Builds the site with Hugo 0.134.2 (extended) and deploys it to Pages on every push to `main`. The planner workflow also calls it. |
| Planner workflow | `.github/workflows/plan-dinners.yaml` | Runs tests and the planner, commits the plan to `main`, then calls the deploy workflow. |
| Other automations | `automations/*.py` | `import_recipe.py` turns a URL or HTML file into a recipe using OpenAI. `group_ingredients.py` and `create_shopping_list.py` are unfinished experiments. See [development.md](development.md#other-automation-scripts). |

## Repo layout

```
.github/workflows/   deploy (hugo.yaml) and weekly planner (plan-dinners.yaml)
archetypes/          `hugo new` templates (meal_plans.md still produces the legacy plan format)
automations/         Python: meal_planner package, tests, recipe import script, experiments
content/recipes/     recipes (the file name without .md is the recipe's "slug")
content/meal_plans/  weekly meal plans, named after the Monday they start on
data/                nursery menu and similarity cache (Hugo can also read these)
docs/                this documentation; docs/vision/README.md is the product spec
layouts/             Hugo templates
static/styles.css    the only stylesheet
new/                 git-ignored scratch area for private drafts (never commit it)
```

## Key design decisions

- **Static site, no server.** Everything the meal planner needs fits a static site: a scheduled job, a manual trigger and published results. GitHub Actions provides the schedule and the manual trigger, and GitHub Pages does the hosting for free. Moving to a server (e.g. Heroku) was considered and rejected for the planner. Part 1 of the vision, a password-protected recipe import page, would need one if it is ever built.
- **Git is the database.** Plans, recipes and generated data are all files, so everything is reviewable, editable by hand and versioned. The planner workflow commits to `main` weekly.
- **The LLM is used once per recipe, and the result is cached.** Judging whether a dinner is "very similar" to a nursery lunch dish means comparing Spanish dish names with English or Spanish recipes, which an LLM does well. Each result is cached with a fingerprint, so planning is deterministic, cheap and inspectable. Recipes are only re-judged when they or the menu change.
- **The rules are prioritised, not hard constraints.** The planner minimises violations rule by rule in priority order, so the plan is still sensible when there are too few recipes to meet every rule. See [meal-planner.md](meal-planner.md#rules).
- **The repo and site are public.** Never commit anything that identifies the owner's son's nursery (its name, the city, etc.). `new/` is git-ignored for this reason.
