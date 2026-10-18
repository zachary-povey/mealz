# Development

## Prerequisites

- **Hugo 0.134.2 extended**, to match CI. Newer versions probably work, but CI is the reference. To install a matching binary without touching your system:
  ```bash
  curl -sSL https://github.com/gohugoio/hugo/releases/download/v0.134.2/hugo_extended_0.134.2_darwin-universal.tar.gz | tar xz hugo
  ```
- **Python 3.10+.** CI uses 3.12.
- **`gh` CLI**: optional, for triggering and watching workflows.

## Python setup and tests

The planner has its own lean requirements file. `automations/requirements.txt` is for the other scripts and pulls in Selenium and other heavy packages.

```bash
cd automations
python -m venv venv                   # automations/venv/ is git-ignored
source venv/bin/activate
pip install -r meal_planner/requirements.txt
python -m pytest -q                   # pytest.ini sets pythonpath and testpaths
```

The tests make no network calls. The OpenAI client is exercised through an `httpx.MockTransport`, and the planner is tested with fake similarity judges. CI runs the same tests before every planner run.

## Building and previewing the site

```bash
hugo server                                         # live reload at http://localhost:1313/ (restart.sh does this after clearing public/)
hugo --destination /tmp/mealz --baseURL http://localhost:8000/ && python3 -m http.server -d /tmp/mealz 8000
```

Use the second form to check production-like output with your local CSS (see [website.md](website.md#gotchas)). Headless Chrome screenshots can't go below a 500px layout width, so at smaller sizes they crop the page rather than reflowing it.

## Deploying

- **Any push to `main` deploys** via `.github/workflows/hugo.yaml` in about a minute. There is no staging environment.
- **The planner bot also commits to `main`** every Wednesday, and whenever someone runs the workflow by hand. Pull before pushing. If you have local changes and your git is set to pull with rebase, stash first or use `git fetch && git merge --ff-only origin/main`.
- Secrets and variables live in the GitHub repo settings: secret `OAI_KEY`, and optional variable `OPENAI_MODEL`.

## Conventions

- **Python:**
  - Type hints on all arguments and return values.
  - Google-style docstrings on public functions and classes.
  - Minimal comments.
  - Raise informative errors rather than silently doing the wrong thing: the planner fails loudly on malformed content.
  - A formatter runs on save, so match its output.
- **Planner logic:** keep `planner.py` free of I/O so it stays easy to test. Put file access in `recipes.py`, `nursery.py`, `meal_plans.py` and `similarity.py`.
- **Templates:** fail the build with `errorf` on broken content (e.g. a missing recipe) rather than rendering something wrong.
- **Generated files** (`content/meal_plans/<date>.md`, `data/lunch_similarity.yaml`) are committed. They can be hand-edited, but re-planning a week or re-judging a recipe overwrites them.

## Privacy

The repo and site are **public**. Never commit or publish:
- the name of the owner's son's nursery;
- the city or anything else that would locate the child.

`new/` is a git-ignored scratch folder for private drafts, such as AI-generated meal plan pages that name the nursery. Keep it out of git. The nursery menu itself is fine to publish, as long as it isn't identified.

## Other automation scripts

| Script | Status | Notes |
| --- | --- | --- |
| `automations/import_recipe.py` | In use | `OAI_KEY=… RECIPE=<url-or-html-path>[,…] python import_recipe.py`. Uses OpenAI to split a page into title, ingredients, method and servings, then convert the ingredients to per-serving quantities and insert `ingredient_mention` shortcodes. Writes `content/recipes/<title_snake>.md` with `tags: []`; add `dinner` by hand for the planner. Falls back to headless Selenium on HTTP 403. |
| `automations/group_ingredients.py` | Experiment | Asks OpenAI to group synonymous ingredient names across all recipes; only prints the result. |
| `automations/create_shopping_list.py` | Unfinished | Early attempt at a Trello shopping list with fuzzy ingredient matching. Reads the legacy `meals` plan format and expects an adjectives word list that isn't where it looks. Not used; the website's shopping list replaced it. |

## Known gaps and ideas

- Ingredient names and units aren't normalised, so shopping lists can list the same item twice (Spanish vs English names, cups vs ml). The vision wants imports converted to metric.
- The nursery menu has no concept of closures or holidays. Re-anchor it when the nursery's rotation shifts (see [content.md](content.md#nursery-menu-datanursery_menuyaml)).
- There is no preference for variety across weeks: consecutive weeks can share dinners (except Sunday→Monday).
- Vision part 1's password-protected import page isn't built. It would need a server or other backend, because the site is static.
