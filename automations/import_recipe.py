import os
from pydantic import BaseModel
from openai import OpenAI
import requests
import yaml
from datetime import date
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from chromedriver_py import binary_path


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

    def to_markdown(self, url: str | None = None) -> str:
        md = "---\n"
        md += yaml.dump(
            {
                "title": self.title,
                "date": date.today().isoformat(),
                "tags": [],
                "ingredients": [ing.model_dump() for ing in self.ingredients],
                "original_url": url,
            },
            indent=4,
            allow_unicode=True,
        )
        md += "---\n"
        md += f"\n{self.instructions}"
        return md


def main(client: OpenAI, recipe_location: str) -> None:
    print("Doing manual preprocessing...")
    recipe_html = get_recipe_html(recipe_location)
    print("Formatting as recipe object...")
    raw_recipe = get_raw_recipe(recipe_html, client)
    print("Normalizing ingredients...")
    ingredients_sorted = get_ingredients_sorted(raw_recipe, client)
    print("Templating Instructions...")
    final_recipe = replace_ingredient_mentions(ingredients_sorted, client)
    print("Outputting...")
    script_dir = os.path.dirname(__file__)
    filename = final_recipe.title.replace(" ", "_").replace("'", "").lower()
    filepath = os.path.join(script_dir, "..", "content", "recipes", f"{filename}.md")

    with open(filepath, "w") as file:
        file.write(final_recipe.to_markdown(recipe_location))


def get_recipe_html(recipe_location: str) -> str:
    if os.path.isfile(recipe_location):
        with open(recipe_location, "r") as file:
            return file.read()
    else:
        try:
            response = requests.get(recipe_location)
            response.raise_for_status()
            return response.text
        except requests.HTTPError as e:
            if e.response.status_code == 403:
                print("Got a 403, trying with selenium...")
                svc = webdriver.ChromeService(executable_path=binary_path)
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                driver = webdriver.Chrome(service=svc, options=chrome_options)
                driver.get(recipe_location)
                html = driver.page_source
                driver.close()
                return html
            raise


def get_raw_recipe(recipe_html: str, client: OpenAI) -> RawRecipe:
    soup = BeautifulSoup(recipe_html, "html.parser")
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    (
                        "Take input recipe html and split into title, ingredients, instructions and servings. "
                        "Make sure the title only has alphanumeric characters and spaces."
                    )
                ),
            },
            {
                "role": "user",
                "content": soup.get_text(),
            },
        ],
        response_format=RawRecipe,
    )
    response = completion.choices[0].message.parsed
    assert response is not None, "Null response!"
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

                3. Simplify the ingredient name: make it a simple name made up of only letters and spaces, make it lower case, drop un-necessary words and move any preparation instructions from the ingredient name (e.g. finely chopped) to extra steps at the beginning of the recipe instructions.

                4. Format the instructions: make them a simple list of steps, one per line in a numbered list.

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
                    "instructions": "1. Chop the onions finely.\n2. Preheat the oven to 180C.\n3. Mix the onions, flour and egg together.\n4. Bake for 30 minutes.",
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
    return response


def replace_ingredient_mentions(recipe: Recipe, client: OpenAI) -> Recipe:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": f"""
                    Take these recipe instructions and replace any mentions of ingredients with:
                    {{{{< ingredient_mention name="ingredient_name" fraction="fraction_used" >}}}},
                    where fraction represents the fraction of the total amount of that ingredient used at that step in the recipe.

                    For example:

                    'Add half the flour' would become {{{{< ingredient_mention name="flour" fraction="0.5" >}}}}.
                    'Use a quarter of the sugar' would become {{{{< ingredient_mention name="sugar" fraction="0.25" >}}}}.

                    If the entire amount is used, use 1.0 for fraction. Please replace all such mentions consistently in the recipe instructions.

                    For the "ingredient_name", use the appropriate string from this list (may differ slightly from the name as it is is mentioned in the instructions): 
                    ```
                    {[ing.name for ing in recipe.ingredients]}
                    ```
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
        recipes = os.environ["RECIPE"].split(",")
    except KeyError as e:
        raise ValueError(f"Missing required environment variable '{e}'")
    client = OpenAI(api_key=api_key)
    for recipe in recipes:
        print(f"Importing: {recipe}")
        main(client, recipe)
