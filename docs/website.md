# Website (Hugo)

The site is built with Hugo **0.134.2 extended**; the version is pinned in `.github/workflows/hugo.yaml`. There is no theme: all templates are in `layouts/` and all CSS is in `static/styles.css`.

## Pages

| URL | Template | Notes |
| --- | --- | --- |
| `/` | `layouts/index.html` | Redirects (meta refresh) to `./meal_plans` |
| `/meal_plans/` | `layouts/meal_plans/list.html` | Dinner plans in weekly blocks |
| `/meal_plans/<date>/` | `layouts/meal_plans/single.html` | That week's shopping list |
| `/recipes/` | `layouts/_default/section.html` | Paginated list of recipes, newest first |
| `/recipes/<slug>/?portions=N` | `layouts/recipes/single.html` | Recipe with quantities scaled to N servings |

Shared: `layouts/_default/baseof.html` (page shell), `layouts/partials/head.html`, `layouts/shortcodes/ingredient_mention.html`.

## Dinner plans page (`meal_plans/list.html`)

- Renders every plan in `plan_start` order as a `<section class="week" data-end="…">`. Each section has a "Shopping list" link and a table of Day | Dinner | Nursery lunch (linked to the recipe with `?portions=`). Legacy plans are shown as a simple list.
- **Inline JavaScript** decides what's current using the viewer's local date. Weeks whose `plan_end` is before today are moved into a collapsed `<details id="past-weeks">`, newest first. Today's row gets the `today` class (highlighted), and a message is shown if there are no current or upcoming weeks. Without JavaScript, every week is shown.
- Hugo can't do the "current week" logic itself: the site is only rebuilt when content changes, so a value computed at build time would go stale.
- Shows `relaxed_rules` as a note if the planner couldn't meet every rule.
- The footer links to the planner workflow (`params.plannerWorkflowURL` in `hugo.yaml`) for manual re-planning.
- Under 600px wide, CSS turns each table row into a grid and moves the nursery lunch under the dinner, so it fits on a phone.

## Shopping list page (`meal_plans/single.html`)

- `partials/meal_plan_entries.html` turns either plan format into a list of `{page, portions, label, date?, lunch?}` entries. `label` is the weekday (e.g. "Mon") for day-by-day plans, or the recipe title for legacy plans.
- Ingredients are summed per name and unit as `quantity_per_serving.value × portions`, using `newScratch` maps. Each ingredient shows the days (labels) that need it. Totals of 10 or more are rounded to whole numbers; smaller totals are shown to 2 decimal places with trailing zeros removed. Zero quantities show the name only.
- Ticks are stored in `localStorage` under `mealz-shopping-<plan file name>` (per browser only). There is a "Clear ticks" button.

## Recipe page (`recipes/single.html`)

The serving selector (1–18, default 2) reloads the page with `?portions=N`. JavaScript fills in each ingredient line and each `ingredient_mention` span with the scaled quantity. Mentions are found with the CSS class `<ingredient name with spaces as underscores>`, so mention names must exactly match ingredient names.

## Gotchas

- **Links must be relative.** The site is served under `/mealz/` and `hugo.yaml` sets `relativeURLs` and `canonifyURLs`. Use `.RelPermalink` and never hard-code paths starting with `/`. The CSS link becomes an absolute URL to the live site via `canonifyURLs`, so when previewing locally build with `--baseURL http://localhost:<port>/`, or you'll see the live CSS rather than your local changes.
- **`site.GetPage` returns an empty placeholder page, not nil, for a missing path.** Check `(and $p $p.IsPage)`. `meal_plan_entries.html` uses `errorf` when a plan references a missing recipe, so the build fails loudly instead of rendering a blank link.
- **`buildFuture: true`** is set so that a plan file whose `date` is in the future (e.g. one created with `hugo new`) is still published.
- The build logs `found no layout file for "html" for kind "taxonomy"/"term"` warnings. They are harmless (tag pages aren't used).
- Minified production HTML drops attribute quotes (`data-date=2026-10-19`). Selectors in the JavaScript still work, but don't parse the HTML with regexes that expect quotes.
- Everything published is public, so keep identifying details about the owner's son's nursery out of templates and content.
