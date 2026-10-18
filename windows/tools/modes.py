from tools.registry import register, run_tool
from memory.database import get_mode, set_mode

DEFAULT_MODES = {
    "work": {"apps": ["notepad++", "pycharm"], "brightness": 80},
    "study": {"apps": ["notepad++"], "brightness": 70},
    "gaming": {"apps": [], "brightness": 100},
    "privacy": {"apps": [], "brightness": None},
}

@register("activate_mode", "Activate work/study/gaming/privacy or a custom local mode. arguments={name}")
def activate_mode(name):
    key = str(name).lower().strip()
    cfg = get_mode(key) or DEFAULT_MODES.get(key)
    if not cfg:
        return f"Mode '{name}' is not configured."
    results = []
    for app in cfg.get("apps", []):
        ok, msg = run_tool("open_application", {"target": app})
        results.append(msg)
    if cfg.get("brightness") is not None:
        ok, msg = run_tool("set_brightness", {"percent": cfg["brightness"]})
        results.append(msg)
    return f"{key.title()} mode activated. " + " ".join(results)

@register("configure_mode", "Configure a mode. arguments={name,apps?,brightness?}")
def configure_mode(name, apps=None, brightness=None):
    cfg = {"apps": list(apps or []), "brightness": brightness}
    set_mode(name, cfg)
    return f"Mode '{name}' saved."
