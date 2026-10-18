from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPES_DIR = REPO_ROOT / "content" / "recipes"
MEAL_PLANS_DIR = REPO_ROOT / "content" / "meal_plans"
NURSERY_MENU_PATH = REPO_ROOT / "data" / "nursery_menu.yaml"
SIMILARITY_CACHE_PATH = REPO_ROOT / "data" / "lunch_similarity.yaml"
