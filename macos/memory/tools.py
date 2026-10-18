from tools.registry import register
from memory.database import (
    remember as db_remember, recall as db_recall, set_preference as db_set_preference,
    get_preference as db_get_preference, all_preferences, set_alias as db_set_alias,
    all_aliases, recent_tasks
)

@register("remember", "Store a user-provided fact. arguments={key,value}")
def remember(key, value):
    db_remember(key, value)
    return f"I'll remember {key}."

@register("recall", "Recall a stored fact. arguments={key}")
def recall(key):
    return db_recall(key) or "I don't have that in memory."

@register("set_preference", "Store a user preference. arguments={key,value}")
def set_preference(key, value):
    db_set_preference(key, value)
    return f"Preference saved: {key} = {value}"

@register("get_preference", "Read a saved preference. arguments={key}")
def get_preference(key):
    return db_get_preference(key) or "No saved preference."

@register("list_preferences", "List saved preferences. arguments={}")
def list_preferences():
    rows = all_preferences()
    return "\n".join(f"{k}: {v}" for k, v in rows) or "No saved preferences."

@register("set_alias", "Create a command/application alias. arguments={alias,target}")
def set_alias(alias, target):
    db_set_alias(alias, target)
    return f"Alias '{alias}' now means '{target}'."

@register("list_aliases", "List command/application aliases. arguments={}")
def list_aliases():
    rows = all_aliases()
    return "\n".join(f"{a} -> {t}" for a, t in rows) or "No aliases."

@register("task_history", "Show recent requests and results. arguments={limit?}")
def task_history(limit=5):
    rows = recent_tasks(limit)
    return "\n".join(f"{when}: {req} -> {res[:160]}" for req, res, when in rows) or "No task history."
