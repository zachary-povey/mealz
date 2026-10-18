import re
from dataclasses import dataclass
from pathlib import Path

import frontmatter

_INGREDIENT_MENTION = re.compile(
    r'\{\{<\s*ingredient_mention\s+name="([^"]*)"[^>]*>\}\}'
)


@dataclass(frozen=True)
class Recipe:
    """A recipe from the recipe book.

    Attributes:
        slug: The recipe's file name without extension, which is also its id in meal plans.
        title: The human readable recipe title.
        tags: The recipe's tags, lower cased.
        ingredients: The names of the recipe's ingredients.
        instructions: The method, with ingredient mention shortcodes replaced by the ingredient name.
    """

    slug: str
    title: str
    tags: tuple[str, ...]
    ingredients: tuple[str, ...]
    instructions: str


def load_recipe(path: Path) -> Recipe:
    """Load a recipe from a markdown file with YAML front matter.

    Args:
        path: Path to the recipe markdown file.

    Returns:
        The parsed recipe.

    Raises:
        ValueError: If the front matter is missing a title or has malformed tags or ingredients.
    """
    post = frontmatter.load(path)
    title = post.metadata.get("title")
    if not title:
        raise ValueError(f"Recipe {path} has no title")

    raw_tags = post.metadata.get("tags") or []
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]
    if not isinstance(raw_tags, list):
        raise ValueError(f"Recipe {path} has tags that are not a list: {raw_tags!r}")

    raw_ingredients = post.metadata.get("ingredients") or []
    try:
        ingredients = tuple(str(ingredient["name"]) for ingredient in raw_ingredients)
    except (TypeError, KeyError) as e:
        raise ValueError(f"Recipe {path} has an ingredient without a name") from e

    return Recipe(
        slug=path.stem,
        title=str(title),
        tags=tuple(str(tag).strip().lower() for tag in raw_tags),
        ingredients=ingredients,
        instructions=_INGREDIENT_MENTION.sub(r"\1", post.content).strip(),
    )


def load_recipes_with_tag(recipes_dir: Path, tag: str) -> list[Recipe]:
    """Load all published recipes that have the given tag.

    Args:
        recipes_dir: Directory containing the recipe markdown files.
        tag: Tag to filter on (case insensitive).

    Returns:
        The matching recipes, sorted by slug.
    """
    recipes = []
    for path in sorted(recipes_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        if frontmatter.load(path).metadata.get("draft"):
            continue
        recipe = load_recipe(path)
        if tag.lower() in recipe.tags:
            recipes.append(recipe)
    return recipes
