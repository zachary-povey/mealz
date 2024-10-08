import os
from pprint import pprint
from pydantic import BaseModel
from openai import OpenAI
import requests
import yaml
from datetime import date


class RawRecipe(BaseModel):
    title: str
    ingredients: list[str]
    instructions: str
    servings: int


class QuantityPerServing(BaseModel):
    value: float | int
    units: str | None


class Ingredient(BaseModel):
    name: str
    quantity_per_serving: QuantityPerServing


class Recipe(BaseModel):
    title: str
    ingredients: list[Ingredient]
    instructions: str

    def to_markdown(self) -> str:
        md = "---\n"
        md += yaml.dump(
            {
                "title": self.title,
                "date": date.today().isoformat(),
                "tags": [],
                "ingredients": [ing.model_dump() for ing in self.ingredients],
            },
            indent=4,
        )
        md += "---\n"
        md += f"# {self.title}\n\n{self.instructions}"
        return md


def main(client: OpenAI, recipe_location: str) -> None:
    recipe_html = get_recipe_html(recipe_location)
    raw_recipe = get_raw_recipe(recipe_html, client)
    ingredients_sorted = get_ingredients_sorted(raw_recipe, client)
    final_recipe = replace_ingredient_mentions(ingredients_sorted, client)

    script_dir = os.path.dirname(__file__)
    filename = final_recipe.title.replace(" ", "_").replace("'", "").lower()
    filepath = os.path.join(script_dir, "..", "content", "recipes", f"{filename}.md")

    with open(filepath, "w") as file:
        file.write(final_recipe.to_markdown())


def get_recipe_html(recipe_location: str) -> str:
    if os.path.isfile(recipe_location):
        with open(recipe_location, "r") as file:
            return file.read()
    else:
        response = requests.get(recipe_location)
        response.raise_for_status()
        return response.text


def get_raw_recipe(recipe_html: str, client: OpenAI) -> RawRecipe:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    (
                        "Take input recipe html and split into title, ingredients, instructions and servings."
                    )
                ),
            },
            {
                "role": "user",
                "content": recipe_html,
            },
        ],
        response_format=RawRecipe,
    )
    response = completion.choices[0].message.parsed
    assert response is not None, "Null response!"
    pprint(response.model_dump())
    return response


def get_ingredients_sorted(raw_recipe: RawRecipe, client: OpenAI) -> Recipe:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """
                Take a structured recipe input and transform it into the specified response format as follows:

                1. Split the ingredients into three parts: the ingredient name, the quantity, and the unit (e.g. grams, ml etc. you can also use pseudo-units like "large" - if no unit is appropriate, e.g. "2 onions" with no size specified, set the units value to null).
                
                2. Convert the quantity into a per-serving quantity: dividing the quantity by the total number of servings specified in the 'servings' key.

                3. Simplify the ingredient name: move any preparation instructions from the ingredient name (e.g. finely chopped) to extra steps at the beginning of the recipe instructions.

                4. Format the instructions: make them a simple list of steps, one per line with a bullet point.

                So for example:
                {
                    "title": "Example Recipe",
                    "ingredients": [
                        "2 onions, finely chopped",
                        "200g of flour",
                        "1 large egg"
                    ],
                    "instructions": "Preheat the oven to 180C. Mix the onions, flour and egg together. Bake for 30 minutes.",
                    "",
                    "servings": 4
                }
                would become something like:
                {
                    "title": "Example Recipe",
                    "ingredients": [
                        {
                            "name": "onions",
                            "quantity_per_serving": {
                                "value": 0.5,
                                "units": null
                            }
                        },
                        {
                            "name": "flour",
                            "quantity_per_serving": {
                                "value": 50,
                                "units": "g"
                            }
                        },
                        {
                            "name": "egg",
                            "quantity_per_serving": {
                                "value": 0.25,
                                "units": large
                            }
                        }
                    ]
                    "instructions": "- Chop the onions finely.\n- Preheat the oven to 180C.\n- Mix the onions, flour and egg together.\n- Bake for 30 minutes.",
                }
            """,
            },
            {
                "role": "user",
                "content": raw_recipe.model_dump_json(),
            },
        ],
        response_format=Recipe,
    )
    response = completion.choices[0].message.parsed
    assert response is not None, "Null response!"
    pprint(response.model_dump())
    return response


def replace_ingredient_mentions(recipe: Recipe, client: OpenAI) -> Recipe:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """
                    Take these recipe instructions and replace any mentions of ingredients with:
                    {{< ingredient_mention name="ingredient_name" fraction="fraction_used" >}},
                    where fraction represents the fraction of the total amount of that ingredient used at that step in the recipe.

                    For example:

                    'Add half the flour' would become {{< ingredient_mention name="flour" fraction="0.5" >}}.
                    'Use a quarter of the sugar' would become {{< ingredient_mention name="sugar" fraction="0.25" >}}.

                    If the entire amount is used, use 1.0 for fraction. Please replace all such mentions consistently in the recipe instructions.
                """,
            },
            {
                "role": "user",
                "content": recipe.instructions,
            },
        ],
    )
    response = completion.choices[0].message.content
    assert response is not None, "Null response!"
    return Recipe(
        title=recipe.title,
        ingredients=recipe.ingredients,
        instructions=response,
    )


if __name__ == "__main__":
    try:
        api_key = os.environ["OAI_KEY"]
        recipe = os.environ["RECIPE"]
    except KeyError as e:
        raise ValueError(f"Missing required environment variable '{e}'")
    client = OpenAI(api_key=api_key)
    main(client, recipe)
