from pathlib import Path

from config import MAX_TOOL_RETRIES
from core.cancellation import TaskCancelled
from core.permissions import permission_for, AUTO, CONFIRM
from core.state import STATE
from core.undo import UNDO
from core.verifier import verify
from tools.registry import run_tool, TOOLS


def _cancelled(cancel_event):
    return bool(cancel_event and cancel_event.is_set())


def _checkpoint(cancel_event):
    if _cancelled(cancel_event):
        raise TaskCancelled("Task cancelled.")


def _substitute(value, last_result, results):
    if isinstance(value, str):
        if value == "$last":
            return last_result

        for index, item in enumerate(results, 1):
            value = value.replace(f"$step{index}", item)

        return value

    if isinstance(value, list):
        return [
            _substitute(item, last_result, results)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            key: _substitute(item, last_result, results)
            for key, item in value.items()
        }

    return value


def _capture_undo(name, args):
    if name == "create_folder":
        return (
            "delete_path",
            {"path": args["path"]},
            f"remove created folder {args['path']}",
        )

    if name == "copy_file":
        return (
            "delete_path",
            {"path": args["destination"]},
            f"remove copied file {args['destination']}",
        )

    if name == "move_file":
        return (
            "move_file",
            {
                "source": args["destination"],
                "destination": args["source"],
            },
            f"move {args['destination']} back to {args['source']}",
        )

    if name == "rename_file":
        original = Path(str(args["path"]))
        new_path = str(original.with_name(str(args["new_name"])))
        return (
            "rename_file",
            {
                "path": new_path,
                "new_name": original.name,
            },
            f"restore name {original.name}",
        )

    return None


def execute(plan, confirm, cancel_event=None):
    results = []
    raw_results = []
    steps = plan.get("steps", [])

    for index, step in enumerate(steps, 1):
        _checkpoint(cancel_event)

        name = step.get("tool")
        args = _substitute(
            step.get("arguments") or {},
            raw_results[-1] if raw_results else "",
            raw_results,
        )

        if name not in TOOLS:
            results.append(f"Step {index}: blocked unknown tool {name}.")
            break

        try:
            level = permission_for(name, args)
        except TypeError:
            # Compatibility with older permission modules.
            level = permission_for(name)

        if level == CONFIRM:
            _checkpoint(cancel_event)

            if not confirm(name, args):
                _checkpoint(cancel_event)
                results.append(f"Step {index}: cancelled.")
                break

        if level not in {AUTO, CONFIRM}:
            results.append(f"Step {index}: blocked by permissions.")
            break

        _checkpoint(cancel_event)
        undo = _capture_undo(name, args)

        STATE.set(
            "EXECUTING",
            f"{index}/{len(steps)} {name}",
        )

        ok = False
        output = ""

        for _ in range(MAX_TOOL_RETRIES + 1):
            _checkpoint(cancel_event)
            ok, output = run_tool(name, args)
            _checkpoint(cancel_event)

            if ok:
                break

        raw_results.append(output)
        results.append(f"Step {index}: {output}")

        if not ok:
            STATE.set("ERROR", output)
            break

        _checkpoint(cancel_event)
        STATE.set("VERIFYING", name)
        verified, verification = verify(name, args, output)
        _checkpoint(cancel_event)

        if not verified:
            results.append(f"Verification: {verification}")
            break

        if undo:
            UNDO.push(*undo)

    _checkpoint(cancel_event)

    if not results and plan.get("response"):
        return plan["response"]

    return "\n".join(results)


def undo_last(confirm, cancel_event=None):
    _checkpoint(cancel_event)
    action = UNDO.pop()

    if not action:
        return "There is nothing reversible to undo."

    if not confirm(action.tool, action.arguments):
        _checkpoint(cancel_event)
        UNDO.items.append(action)
        return "Undo cancelled."

    _checkpoint(cancel_event)
    ok, result = run_tool(action.tool, action.arguments)
    _checkpoint(cancel_event)

    return f"Undo: {result}" if ok else f"Undo failed: {result}"
