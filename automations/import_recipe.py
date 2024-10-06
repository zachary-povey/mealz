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
                "content": (
                    (
                        "Take this formatted recipe and simplify the ingredients such that "
                        "any preparation (like chopping) is moved into the instructions. "
                        "Make sure the instructions are formatted as a list of steps."
                        "Then convert the numeric quantity of the ingredients to a value "
                        "per serving (by dividing by the total servings specified in the "
                        "'servings' key. Split the ingredient's units and the value. Where "
                        "units don't make sense (for example whole numbers of vegetables) "
                        "return null."
                    )
                ),
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
                "content": (
                    (
                        "Take the recipe and replace any mentions of ingredients with "
                        '\'{{< ingredient_mention name="the_ingredient_name" fraction="fraction_used">}}\''
                        "where fraction refers to the fraction of the total amount of that ingredient used at"
                        "that point in the recipe. For example 'add half the flour' would be replaced by: "
                        '\'{{< ingredient_mention name="flour" fraction="0.5">}}\'.'
                    )
                ),
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
