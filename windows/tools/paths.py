import os
from pathlib import Path
from config import ALLOW_OUTSIDE_USER_PROFILE

HOME = Path.home().resolve()

SPECIAL = {
    "home": HOME,
    "desktop": HOME / "Desktop",
    "documents": HOME / "Documents",
    "downloads": HOME / "Downloads",
    "pictures": HOME / "Pictures",
    "music": HOME / "Music",
    "videos": HOME / "Videos",
}

# Prefer OneDrive redirected folders if present.
ONEDRIVE = Path(os.environ.get("OneDrive", HOME / "OneDrive"))
for key in ("desktop", "documents", "pictures"):
    candidate = ONEDRIVE / key.capitalize()
    if candidate.exists():
        SPECIAL[key] = candidate

def resolve_path(value):
    raw = str(value).strip()
    lower = raw.lower().replace("\\", "/")
    for name, base in SPECIAL.items():
        if lower == name:
            p = base
            break
        if lower.startswith(name + "/"):
            p = base / raw[len(name) + 1:]
            break
    else:
        p = Path(os.path.expandvars(os.path.expanduser(raw)))
        if not p.is_absolute():
            p = HOME / p

    p = p.resolve()
    if ALLOW_OUTSIDE_USER_PROFILE:
        return p
    if p == HOME or HOME in p.parents:
        return p
    if p == ONEDRIVE or ONEDRIVE in p.parents:
        return p
    raise PermissionError("File access is restricted to your Windows user profile.")
