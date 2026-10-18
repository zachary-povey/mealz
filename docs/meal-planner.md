# Dinner planner

The planner implements part 2 of the [vision](vision/README.md). Each Wednesday it plans the dinners for the week starting the following Monday. It picks recipes tagged `dinner` and keeps them clear of the son's nursery lunches. It can also be run by hand, and it always plans the upcoming week, replacing any existing plan for that week.

## Where things are

| File | Responsibility |
| --- | --- |
| `automations/meal_planner/__main__.py` | CLI entry point: loads everything, plans, prints the plan, writes it |
| `automations/meal_planner/planner.py` | The rules and the optimiser (pure logic, no I/O) |
| `automations/meal_planner/similarity.py` | OpenAI similarity judge and the cache in `data/lunch_similarity.yaml` |
| `automations/meal_planner/nursery.py` | Loads `data/nursery_menu.yaml`; works out the rotation week and lunch for any date |
| `automations/meal_planner/recipes.py` | Loads recipes from `content/recipes` and filters by tag (drafts skipped) |
| `automations/meal_planner/meal_plans.py` | Finds the upcoming Monday, finds/replaces existing plans, writes plan files |
| `automations/meal_planner/paths.py` | Repo paths (derived from the package location) |
| `automations/tests/` | pytest suite (run from `automations/`) |
| `.github/workflows/plan-dinners.yaml` | Weekly schedule, manual trigger, commit and deploy |

## What a run does

1. Works out **today** in `Europe/Madrid` and the **upcoming Monday**: the first Monday strictly after today, so a run on a Monday plans the following week.
2. Loads the nursery menu, and every non-draft recipe tagged `dinner`. Fails if there are none.
3. **Resolves lunch similarity** for each recipe from the cache. Recipes that are new or changed are judged by OpenAI and the cache is rewritten (see [below](#lunch-similarity)).
4. Builds 7 slots (Mon–Sun), each with that day's nursery lunch (empty at weekends). It also looks up the **previous day's dinner** (the Sunday before) from an existing plan, so it can avoid repeating it.
5. **Optimises** the plan (see [Rules](#rules)) and prints it, including any rules it couldn't meet.
6. **Writes** `content/meal_plans/<monday>.md`, overwriting that file and deleting any other plan whose `plan_start` falls within the same week.

The workflow then commits `content/meal_plans/` and `data/lunch_similarity.yaml` to `main` and deploys the site.

## Rules

These rules come from the vision, in priority order (`RULES_BY_PRIORITY` in `planner.py`):

1. **Not similar to that day's nursery lunch** (`AvoidSimilarToNurseryLunch`). A dinner breaks the rule if its cached similar dishes include either of the day's lunch dishes.
2. **Not the same dinner two days running** (`AvoidConsecutiveRepeats`), including Sunday→Monday across weeks. The vision's text for this rule is unfinished ("avoiding the same meal"), and this is the chosen interpretation. If the owner clarifies it, change this rule.
3. **Not the same dinner twice in the week** (`AvoidRepeatsWithinWeek`).

**"Discard the lowest priority rules first"** is implemented as a lexicographic optimum. Each candidate plan is scored with a tuple of violation counts `(rule1, rule2, rule3)`, and the smallest tuple wins. A plan with fewer rule 1 violations always beats one with more, whatever happens to rules 2 and 3. Lower priority rules are only relaxed as far as necessary: with 3 recipes you get A,B,C,A,B,C,A rather than an arbitrary mix. Any violations are recorded in the plan's `relaxed_rules` and shown on the website.

**Optimiser** (`plan_dinners`): depth-first branch-and-bound over the 7 days.
- Candidate recipes are shuffled first, so tied plans vary from week to week. Pass `--seed` for a reproducible plan.
- At each day, options are tried cheapest-first.
- A branch is pruned when its cost so far plus a lower bound for the remaining days can't beat the best plan found so far. Each rule provides its own lower bound via `remaining_lower_bound`.
- The search stops as soon as it finds a plan that matches the global lower bound.

The result is provably optimal. It has been checked against brute force on random cases and takes milliseconds even with 40 recipes and many clashes.

**Adding a rule:** subclass `Rule` in `planner.py`. Implement `cost` (the violations caused by placing one recipe, given the recipes already chosen) and `remaining_lower_bound` (returning 0 is always valid, but makes the search slower). Then insert it into `RULES_BY_PRIORITY` at the right priority and add tests in `automations/tests/test_planner.py`.

## Lunch similarity

`similarity.py` decides which nursery lunch dishes each dinner recipe is "the same as or very similar to".

- **Judge:** `OpenAISimilarityJudge` sends one request per recipe, containing the title, ingredient names and the first 2000 characters of the method, plus the full list of menu dishes. It uses structured output: the response schema only allows dish names that are on the menu.
- **Prompt philosophy:** compare the dish as it is eaten. Dishes count as very similar only if they have the same main component prepared in a similar way. A shared broad category (e.g. "both fish"), a shared minor ingredient, or vegetables hidden by blending them into a sauce or stock don't count. An earlier, looser prompt over-matched badly; for example, baked salmon matched every fish dish and turkey strips matched every cream soup. That over-matching quietly shrinks the planner's options.
- **Cache:** results are stored in `data/lunch_similarity.yaml`, keyed by recipe slug with a fingerprint. The fingerprint is a hash of the recipe's title, ingredients and instructions, the sorted list of menu dishes, and `JUDGEMENT_VERSION`. **Bump `JUDGEMENT_VERSION` whenever you change the prompt or the judging logic,** so every recipe is re-judged.
- **No key:** if any recipe needs judging and `OAI_KEY` isn't set, the run fails with a message listing those recipes. When everything is cached, no key is needed.

## Configuration

| Setting | Where | Default |
| --- | --- | --- |
| OpenAI API key | `OAI_KEY` env var; GitHub Actions secret `OAI_KEY` | none (required only for judging) |
| OpenAI model | `OPENAI_MODEL` env var; GitHub Actions repository variable `OPENAI_MODEL` | `gpt-5-mini` (`DEFAULT_OPENAI_MODEL`) |
| Portions per dinner | `--portions`, or `DEFAULT_PORTIONS` in `__main__.py` | 4 |
| Recipe tag | `DINNER_TAG` in `__main__.py` | `dinner` |
| Time zone for "today" | `TIMEZONE` in `__main__.py` | `Europe/Madrid` |
| Schedule | `cron` in `plan-dinners.yaml` | `0 5 * * 3`: Wednesdays 05:00 UTC |

## Running it

```bash
cd automations
python -m meal_planner --dry-run          # print next week's plan, write nothing (the cache may still be updated)
python -m meal_planner                    # write content/meal_plans/<next monday>.md
python -m meal_planner --week-start 2026-11-02 --seed 1   # a specific Monday, reproducibly
```

Running it locally writes into your working tree. In normal use, let the workflow do it, so the plan is committed and deployed.

**Manual re-plan in production:** use the "run the planner" link at the bottom of the plans page, or https://github.com/zachary-povey/mealz/actions/workflows/plan-dinners.yaml → "Run workflow", or `gh workflow run plan-dinners.yaml`. It takes about 2 minutes to appear on the site.

## The workflow

`.github/workflows/plan-dinners.yaml`:

1. **`plan` job:** checks out `main`, installs `automations/meal_planner/requirements.txt`, runs pytest, runs the planner, commits as `github-actions[bot]` ("Plan next week's dinners"), rebases onto `main` and pushes.
2. **`deploy` job:** calls `.github/workflows/hugo.yaml` via `workflow_call`, passing the new commit SHA as `ref`. This is necessary because pushes made with the default `GITHUB_TOKEN` do not trigger other workflows, so the push alone would never redeploy the site.

Other things to know:
- GitHub disables scheduled workflows in public repos after 60 days without repository activity. The weekly bot commit should keep it alive. If plans stop appearing, check the Actions tab and re-enable the workflow if needed.
- The cron time is UTC, so Spanish local time shifts by an hour with daylight saving.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Run fails with "need their similarity to the nursery lunch menu judging" | The `OAI_KEY` secret is missing or invalid |
| Run fails calling OpenAI with a model error | Model retired or not available to the key; set the `OPENAI_MODEL` repository variable |
| Run fails with "No recipes … are tagged 'dinner'" | No recipe has the `dinner` tag (or all are drafts) |
| "lists dishes … that aren't on the nursery menu" | A hand edit in `data/lunch_similarity.yaml` doesn't match a menu dish exactly |
| "Meal plan … has an invalid plan_start" | A plan file is missing a valid `plan_start` |
| A dinner that obviously matches the lunch was still planned | Check its `similar_lunch_dishes` in the cache; edit by hand or improve the prompt and bump `JUDGEMENT_VERSION` |
| The week shows "Not enough dinner recipes to avoid: …" | Too few `dinner` recipes for the rules; add more or tag existing ones |
| Push to `main` rejected | The bot committed a plan; `git pull` first |
