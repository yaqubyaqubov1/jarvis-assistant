from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class Tool:
    name: str
    description: str
    function: Callable

TOOLS = {}

def register(name, description):
    def decorator(fn):
        TOOLS[name] = Tool(name, description, fn)
        return fn
    return decorator

def run_tool(name, arguments=None):
    tool = TOOLS.get(name)
    if not tool:
        return False, f"Unknown tool: {name}"
    try:
        return True, str(tool.function(**(arguments or {})))
    except TypeError as exc:
        return False, f"Invalid arguments for {name}: {exc}"
    except Exception as exc:
        return False, f"{name} failed: {exc}"

def tool_prompt():
    return "\n".join(f"- {name}: {tool.description}" for name, tool in sorted(TOOLS.items()))
