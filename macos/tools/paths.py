"""Resolve user paths without assuming Windows or OneDrive."""
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
    "photos": HOME / "Pictures",
    "music": HOME / "Music",
    "videos": HOME / "Movies",
    "movies": HOME / "Movies",
}

def resolve_path(value):
    raw = str(value).strip()
    if not raw:
        raise ValueError("A file or folder path is required.")
    lower = raw.lower().replace("\\", "/")
    for name, base in SPECIAL.items():
        if lower == name:
            path = base
            break
        if lower.startswith(name + "/"):
            path = base / raw[len(name) + 1:]
            break
    else:
        path = Path(os.path.expandvars(os.path.expanduser(raw)))
        if not path.is_absolute():
            path = HOME / path
    path = path.resolve()
    if ALLOW_OUTSIDE_USER_PROFILE or path == HOME or HOME in path.parents:
        return path
    raise PermissionError("File access is restricted to your macOS home folder.")
