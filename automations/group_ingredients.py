# get all ingedients in big list
# ask chatgpt to group them
#  format:
# ingredients:
#   some_canonical_name:
#     canonical name: some canonical name
#     aliases: []
from pprint import pprint
from typing import List, Set
from openai import OpenAI
from pydantic import BaseModel
import os
import frontmatter

script_dir = os.path.abspath(os.path.dirname(__file__))
content_dir = os.path.abspath(os.path.join(script_dir, "..", "content"))
recipe_dir = os.path.abspath(os.path.join(content_dir, "recipes"))


class Ingredient(BaseModel):
    canonical_name: str
    aliases: List[str]


class IngredientsDB(BaseModel):
    ingredients: List[Ingredient]


def group_ings(ingredients: Set[str], client: OpenAI) -> IngredientsDB:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    (
                        "Take the list of ingredients and group into distinct groups of ingredient names "
                        + "that are either synonyms of each other or are very similar in that they could all "
                        + "be used in place of the others without impacting the recipe. Output in the format specified "
                        + "with  *all* items in the original list that belong to the group in the 'aliases' list and "
                        + " a sensible choice for 'canonical_name'.o Ensure all names in the input list are included in the output."
                    )
                ),
            },
            {
                "role": "user",
                "content": ", ".join(ingredients),
            },
        ],
        response_format=IngredientsDB,
    )
    ings_db = completion.choices[0].message.parsed
    if ings_db is None:
        raise RuntimeError("gpt fail")

    ingredients_output = {alias for ing in ings_db.ingredients for alias in ing.aliases}
    missing = ingredients - ingredients_output

    for i in range(10):
        if len(missing) == 0:
            break
        print(f"Request: {i}")
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        (
                            "Take the list of ingredient names and add each one to the appropriate 'alias' list in the ingredients db object. "
                            + "If there is no appropriate list to put the ingredient in, create a new item in the 'ingredients' list for the ingredient, "
                            + "choosing an appropriate value for 'canonical_name' and putting the value it's self into the 'alias' list."
                        )
                    ),
                },
                {
                    "role": "user",
                    "content": str(ingredients),
                },
                {
                    "role": "user",
                    "content": str(ings_db),
                },
            ],
            response_format=IngredientsDB,
        )
        ings_db = completion.choices[0].message.parsed
        if ings_db is None:
            raise RuntimeError("gpt fail")
        ingredients_output = {
            alias for ing in ings_db.ingredients for alias in ing.aliases
        }
        missing = ingredients - ingredients_output
        print(f"\n\nRequest: {i}")
        print(f"Missing: {missing}")

    return ings_db  # type: ignore


def main() -> None:
    try:
        client = OpenAI(api_key=os.environ["OAI_KEY"])
    except KeyError as e:
        raise ValueError(f"Missing required env var: '{e}'")

    all_ings = set()
    for filename in os.listdir(recipe_dir):
        if filename.startswith("_"):
            continue

        recipe_fpath = os.path.join(recipe_dir, filename)
        recipe: dict = frontmatter.load(recipe_fpath).to_dict()
        ingredients = recipe["ingredients"]
        all_ings.update(ing["name"] for ing in ingredients)

    pprint(group_ings(all_ings, client).model_dump())


if __name__ == "__main__":
    main()
