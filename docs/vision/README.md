# Mealz

This app is a personal tool to help me:

1. Recipe Book: store recipes in a standard format that is readable to me
2. Meal Planner: create meal plans (for dinners only) with associated shopping lists using a set set of recipes that my son likes

## 1. Recipe Book

The app publishes my recipes on a public website so I can view them from anywhere and share them with friends and family.

The app exposes a page for importing new recipes this page is password protected with a simple single password system (single value stored securely and exposed to the app at runtime via an env var), it issues a cookie which means you don't need to log in from the same browser for a month. When a new recipe is imported it converts it into the predefined format:

- All mentions of ingredients give the full quantities, so the reader doesn't have to go back and check the ingredients again
- Ingredients quantities are converted into metric

## 2. Meal Planner

The meal planner functionality creates meal plans (for dinner only) on a weekly schedule: each wednesday it plans the dinners for the week starting on the upcoming Monday. It organises this by picking recipes from the Recipe Book with the tag "dinner", it chooses appropriate dinner recipes for the days applying the following rules, in priority order:

- comparing the chosen recipes to my son's nursery lunchtime meal plan (a constant four-week cycle saved in the repo for this comparison) and avoiding him eating the same meal twice, or two very similar meals, on the same day
- avoiding the same meal
- avoiding the same meal appearing twice in a given week

If all rules cannot be met for some reason, the process should discard the lowest priority rules first.

The meal planning process can also be triggered manually and will always run for the next week (i.e. the week starting on the upcoming monday) - it should replace any meal plans for that week that have already been created.

After the weekly process runs, the new meal plan should appear on the website. The meal plan is shown as weekly blocks (showing the current week and all later weeks planned by default) at the top of the block there should be a link to the shopping list created for that week's meal plan, then within the block it should display the dinner recipe alongside the lunchtime meal my son will be having that day. The name of the dinner recipes should be a link, which when clicked takes you to the recipe for that meal.
