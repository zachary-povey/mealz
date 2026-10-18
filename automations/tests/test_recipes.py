from pathlib import Path

import pytest

from meal_planner.recipes import load_recipe, load_recipes_with_tag


def write_recipe(directory: Path, slug: str, front_matter: str, body: str = "") -> Path:
    path = directory / f"{slug}.md"
    path.write_text(f"---\n{front_matter}\n---\n{body}")
    return path


def test_loads_recipe(tmp_path: Path) -> None:
    path = write_recipe(
        tmp_path,
        "pita_pizzas",
        "title: Pita pizzas\ntags: [Dinner]\ningredients:\n  - name: pitta bread\n  - name: cheese",
        '1. Top the {{< ingredient_mention name="pitta bread" fraction="1.0" >}} with cheese.',
    )

    recipe = load_recipe(path)

    assert recipe.slug == "pita_pizzas"
    assert recipe.tags == ("dinner",)
    assert recipe.ingredients == ("pitta bread", "cheese")
    assert recipe.instructions == "1. Top the pitta bread with cheese."


def test_filters_on_tag_and_skips_drafts_and_index(tmp_path: Path) -> None:
    (tmp_path / "_index.md").write_text("# Recipes")
    write_recipe(tmp_path, "a", "title: A\ntags: [dinner, lunch]")
    write_recipe(tmp_path, "b", "title: B\ntags:\n  - lunch")
    write_recipe(tmp_path, "c", "title: C\ntags: []")
    write_recipe(tmp_path, "d", "title: D\ntags: [dinner]\ndraft: true")
    write_recipe(tmp_path, "e", "title: E\ntags: dinner")

    assert [r.slug for r in load_recipes_with_tag(tmp_path, "dinner")] == ["a", "e"]


def test_rejects_recipe_without_title(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no title"):
        load_recipe(write_recipe(tmp_path, "a", "tags: [dinner]"))
