import importlib.util
from pathlib import Path

def load_custom_skills():
    folder = Path(__file__).resolve().parent / "custom"
    loaded = []
    for path in folder.glob("*.py"):
        if path.name.startswith("_"):
            continue
        name = f"jarvis_custom_{path.stem}"
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        loaded.append(path.stem)
    return loaded
