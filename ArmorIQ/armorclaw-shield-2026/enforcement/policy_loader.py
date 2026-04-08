import yaml
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def load_policies(path: str = "policies/business_rules.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_policies_for_intent(intent_type: str) -> list:
    data = load_policies()
    return [p for p in data["policies"] if intent_type in p["trigger"]]


def get_whitelist() -> dict:
    return load_policies().get("whitelist", {})


def get_all_policies() -> list:
    return load_policies()["policies"]


def reload_policies():
    load_policies.cache_clear()