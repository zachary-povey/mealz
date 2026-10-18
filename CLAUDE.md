# Mealz

A personal recipe book and weekly dinner planner. It's a static Hugo site deployed to GitHub Pages (https://zachary-povey.github.io/mealz/). Content is markdown and YAML in git, and there's no server or database. A Python planner (`automations/meal_planner`) runs every Wednesday in GitHub Actions. It picks next week's dinners from recipes tagged `dinner`, avoiding dinners too similar to the son's nursery lunch, then commits the plan and redeploys.

## Rules that matter

- **The repo and site are public.** Never commit or publish the son's nursery name, the city or anything else that locates him. `new/` is git-ignored for private drafts; keep it that way.
- **A push to `main` deploys to production immediately.** The planner bot also commits to `main` weekly, so fetch before pushing.
- **The recipe file name is its slug.** Meal plans and `data/lunch_similarity.yaml` reference slugs, and the site build fails on purpose if a plan references a missing recipe.
- **Changing the similarity prompt or logic** in `automations/meal_planner/similarity.py` requires bumping `JUDGEMENT_VERSION`.
- **Templates must use relative links** (`.RelPermalink`), because the site is served under `/mealz/`.

## Quick commands

```bash
cd automations && python -m pytest -q             # planner tests (pip install -r meal_planner/requirements.txt)
cd automations && python -m meal_planner --dry-run  # preview next week's plan
hugo server                                        # local site (CI uses Hugo 0.134.2 extended)
gh workflow run plan-dinners.yaml                  # re-plan next week in production
```

## Documentation

Always relevant:

@docs/architecture.md
@docs/development.md

Read these when working in the area:

- [docs/vision/README.md](docs/vision/README.md): product spec written by the owner. Check it before changing behaviour.
- [docs/content.md](docs/content.md): formats for recipes, meal plans, the nursery menu and the similarity cache.
- [docs/meal-planner.md](docs/meal-planner.md): planner rules, optimiser, OpenAI similarity judging, workflow, troubleshooting.
- [docs/website.md](docs/website.md): Hugo templates, page JavaScript, styling, Hugo gotchas.
