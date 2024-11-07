import os
from typing import List, TypedDict
import requests
from dataclasses import dataclass
from datetime import datetime
import frontmatter

script_dir = os.path.abspath(os.path.dirname(__file__))
content_dir = os.path.abspath(os.path.join(script_dir, "..", "content"))


@dataclass
class Config:
    meal_plan: str
    trello_api_key: str
    trello_api_token: str
    trello_board_id: str = "BFSQpAhe"
    trello_list_id: str = "60d3a574235d7b473fe1f60c"
    trello_label_id: str = "6726b65dae5fc163d1766a1e"

    @classmethod
    def from_env(cls):
        try:
            return cls(
                meal_plan=os.environ.get("MEAL_PLAN", "2024-11-01"),
                trello_api_key=os.environ["TRELLO_KEY"],
                trello_api_token=os.environ["TRELLO_TOKEN"],
            )
        except KeyError as e:
            raise ValueError(f"Missing required environment variable: {e}")
    
    @property
    def meal_plan_path(self):
        return os.path.join(
            content_dir,
            "meal_plans",
            f"{self.meal_plan}.md",
        )

class IngredientQuantity(TypedDict):
    units: str | None
    quantity: float

#  specify meal plan
#  fetch front matter yaml from each meal in plan
#  get ingredients, multiply each quantity by portions
#  translate any spanish to english (ai?)
#  name normalization? (ai)
#  department grouping? (ai)
#  convert any imperial units to metric
#  group by name, sum together any equal units, round to two significant figures
#  output - where?


def create_list_in_trello(shopping_list: List[str], config: Config) -> None:
    # create card
    card_id = create_trello_card(
        f"Shopping List: {datetime.now().strftime('%Y-%m-%d %H:%M')}", config
    )

    # add list on card (id)
    checklist_id = create_checklist_in_trello(card_id, "Shopping List", config)

    # add item to list (id) for item in shopping_list
    for item in shopping_list:
        create_checklist_item_in_trello(checklist_id, item, config)


def create_checklist_item_in_trello(
    checklist_id: str, item: str, config: Config
) -> None:
    url = f"https://api.trello.com/1/checklists/{checklist_id}/checkItems"
    headers = {"Accept": "application/json"}

    query = {
        "id": checklist_id,
        "name": item,
        "key": config.trello_api_key,
        "token": config.trello_api_token,
    }

    response = requests.request("POST", url, headers=headers, params=query)
    response.raise_for_status()


def create_trello_card(name: str, config: Config) -> str:
    url = "https://api.trello.com/1/cards"
    headers = {"Accept": "application/json"}

    query = {
        "idList": config.trello_list_id,
        "idLabels": config.trello_label_id,
        "key": config.trello_api_key,
        "token": config.trello_api_token,
        "name": name,
        "pos": "top",
    }

    response = requests.request("POST", url, headers=headers, params=query)
    response.raise_for_status()
    return response.json()["id"]


def create_checklist_in_trello(card_id: str, name: str, config: Config) -> str:
    url = f"https://api.trello.com/1/cards/{card_id}/checklists"
    headers = {"Accept": "application/json"}

    query = {
        "idCard": card_id,
        "key": config.trello_api_key,
        "token": config.trello_api_token,
        "name": name,
    }

    response = requests.request("POST", url, headers=headers, params=query)
    response.raise_for_status()
    return response.json()["id"]

def get_raw_ingredients(config: Config) -> List[dict]:
    #  {"ing": [{"units": "g", "name": "flour", "quantity": 100}]}
    meal_plan = frontmatter.load(config.meal_plan_path).to_dict()
    pass

def main(meal_plan: str):
    config = Config.from_env()
    raw_ingredients = get_raw_ingredients(config)
    # create_list_in_trello(["eggs", "milk", "flour"], config)


if __name__ == "__main__":
    meal_plan = os.getenv("MEAL_PLAN", "2024-11-01")
    main(meal_plan)
