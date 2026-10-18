import json
from collections.abc import Sequence
from pathlib import Path

import httpx
import pytest
import yaml
from openai import OpenAI

from meal_planner.recipes import Recipe
from meal_planner.similarity import LunchSimilarity, OpenAISimilarityJudge

DISHES = ("pasta boloñesa", "tortilla de patatas", "crema de calabaza")


def recipe(slug: str, title: str = "") -> Recipe:
    return Recipe(
        slug=slug,
        title=title or slug,
        tags=("dinner",),
        ingredients=("x",),
        instructions="",
    )


class FakeJudge:
    def __init__(self, answers: dict[str, list[str]]) -> None:
        self.answers = answers
        self.calls: list[str] = []

    def similar_dishes(self, recipe: Recipe, dishes: Sequence[str]) -> list[str]:
        self.calls.append(recipe.slug)
        return self.answers.get(recipe.slug, [])


def test_judges_new_recipes_and_caches_them(tmp_path: Path) -> None:
    cache = tmp_path / "cache.yaml"
    judge = FakeJudge({"bolognese": ["pasta boloñesa"]})

    result = LunchSimilarity(cache, judge).resolve(
        [recipe("bolognese"), recipe("salmon")], DISHES
    )

    assert result == {"bolognese": frozenset({"pasta boloñesa"}), "salmon": frozenset()}
    assert judge.calls == ["bolognese", "salmon"]
    assert set(yaml.safe_load(cache.read_text())) == {"bolognese", "salmon"}


def test_uses_cache_without_a_judge(tmp_path: Path) -> None:
    cache = tmp_path / "cache.yaml"
    LunchSimilarity(cache, FakeJudge({"bolognese": ["pasta boloñesa"]})).resolve(
        [recipe("bolognese")], DISHES
    )

    result = LunchSimilarity(cache, judge=None).resolve([recipe("bolognese")], DISHES)

    assert result == {"bolognese": frozenset({"pasta boloñesa"})}


def test_keeps_hand_edits(tmp_path: Path) -> None:
    cache = tmp_path / "cache.yaml"
    LunchSimilarity(cache, FakeJudge({})).resolve([recipe("bolognese")], DISHES)
    edited = yaml.safe_load(cache.read_text())
    edited["bolognese"]["similar_lunch_dishes"] = ["pasta boloñesa"]
    cache.write_text(yaml.safe_dump(edited, allow_unicode=True))

    result = LunchSimilarity(cache, judge=None).resolve([recipe("bolognese")], DISHES)

    assert result == {"bolognese": frozenset({"pasta boloñesa"})}


def test_rejudges_changed_recipes(tmp_path: Path) -> None:
    cache = tmp_path / "cache.yaml"
    LunchSimilarity(cache, FakeJudge({})).resolve([recipe("bolognese")], DISHES)
    judge = FakeJudge({"bolognese": ["pasta boloñesa"]})

    result = LunchSimilarity(cache, judge).resolve(
        [recipe("bolognese", "Spaghetti bolognese")], DISHES
    )

    assert judge.calls == ["bolognese"]
    assert result["bolognese"] == frozenset({"pasta boloñesa"})


def test_rejudges_when_the_menu_changes(tmp_path: Path) -> None:
    cache = tmp_path / "cache.yaml"
    LunchSimilarity(cache, FakeJudge({})).resolve([recipe("bolognese")], DISHES)
    judge = FakeJudge({})

    LunchSimilarity(cache, judge).resolve(
        [recipe("bolognese")], DISHES + ("macarrones",)
    )

    assert judge.calls == ["bolognese"]


def test_raises_when_judging_is_needed_without_a_judge(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="OAI_KEY"):
        LunchSimilarity(tmp_path / "cache.yaml", judge=None).resolve(
            [recipe("bolognese")], DISHES
        )


def test_raises_on_unknown_cached_dish(tmp_path: Path) -> None:
    cache = tmp_path / "cache.yaml"
    LunchSimilarity(cache, FakeJudge({})).resolve([recipe("bolognese")], DISHES)
    edited = yaml.safe_load(cache.read_text())
    edited["bolognese"]["similar_lunch_dishes"] = ["spaghetti"]
    cache.write_text(yaml.safe_dump(edited))

    with pytest.raises(ValueError, match="spaghetti"):
        LunchSimilarity(cache, judge=None).resolve([recipe("bolognese")], DISHES)


def test_drops_recipes_no_longer_planned(tmp_path: Path) -> None:
    cache = tmp_path / "cache.yaml"
    LunchSimilarity(cache, FakeJudge({})).resolve(
        [recipe("bolognese"), recipe("salmon")], DISHES
    )

    LunchSimilarity(cache, judge=None).resolve([recipe("salmon")], DISHES)

    assert set(yaml.safe_load(cache.read_text())) == {"salmon"}


def openai_client(reply: dict, requests: list[dict]) -> OpenAI:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(reply), "refusal": None},
                    }
                ],
            },
        )

    return OpenAI(api_key="test", http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_openai_judge_restricts_answers_to_menu_dishes() -> None:
    requests: list[dict] = []
    judge = OpenAISimilarityJudge(openai_client({"similar_dishes": ["pasta boloñesa"]}, requests), model="test-model")

    result = judge.similar_dishes(recipe("bolognese", "Spaghetti Bolognese"), DISHES)

    assert result == ["pasta boloñesa"]
    schema = requests[0]["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert set(schema["schema"]["properties"]["similar_dishes"]["items"]["enum"]) == set(DISHES)
    assert "Spaghetti Bolognese" in requests[0]["messages"][1]["content"]


def test_openai_judge_rejects_dishes_not_on_menu() -> None:
    judge = OpenAISimilarityJudge(openai_client({"similar_dishes": ["spaghetti"]}, []), model="test-model")

    with pytest.raises(ValueError):
        judge.similar_dishes(recipe("bolognese"), DISHES)
