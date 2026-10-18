import json
import re

from ai.ollama import chat
from core.cancellation import (
    TaskCancelled,
    begin_task,
    cancel_current_task,
    cancel_event,
    finish_task,
)
from core.executor import execute, undo_last
from core.planner import plan
from core.router import quick_plan, looks_conversational
from core.session import SESSION
from core.state import STATE
from memory.database import save_task


def clean_command(text):
    return re.sub(
        r"^\s*(?:hey\s+)?jarvis\b[\s,.:;!-]*",
        "",
        str(text),
        flags=re.I,
    ).strip()


class Assistant:
    def cancel(self):
        return cancel_current_task()

    def handle(self, command, confirm):
        command = clean_command(command)

        if not command:
            return ""

        lower = command.lower().strip().rstrip(".!?")

        if lower in {
            "stop",
            "cancel",
            "cancel that",
            "stop that",
            "stop task",
            "interrupt",
            "interrupt task",
            "never mind",
            "nevermind",
        }:
            return "Cancelled." if self.cancel() else "There is no active task to cancel."

        if lower in {
            "repeat that",
            "do that again",
            "repeat my last command",
        }:
            from memory.database import recent_tasks

            tasks = recent_tasks(2)
            if not tasks:
                return "There is no previous task to repeat."

            target = tasks[1][0] if len(tasks) > 1 else tasks[0][0]

            if target.lower().strip().rstrip(".!?") == lower:
                return "There is no earlier task to repeat."

            command = target
            lower = command.lower().strip().rstrip(".!?")

        begin_task()
        SESSION.add("user", command)

        try:
            if lower in {
                "undo",
                "undo that",
                "undo last action",
            }:
                result = undo_last(confirm, cancel_event())
                SESSION.add("assistant", result)
                return result

            fast = quick_plan(command)

            if fast is not None:
                task_plan = fast

            elif looks_conversational(command):
                STATE.set("THINKING", "local conversation")
                result = chat(command, SESSION.history)
                SESSION.add("assistant", result)
                save_task(
                    command,
                    json.dumps({"kind": "conversation"}),
                    result,
                )
                return result

            else:
                STATE.set("PLANNING", "local AI")
                task_plan = plan(command)

            if (
                task_plan.get("kind") == "conversation"
                or not task_plan.get("steps")
            ):
                result = str(task_plan.get("response", "")).strip()

                if not result:
                    STATE.set("THINKING", "local conversation")
                    result = chat(command, SESSION.history)

            else:
                result = execute(
                    task_plan,
                    confirm,
                    cancel_event(),
                )

            if cancel_event().is_set():
                raise TaskCancelled("Task cancelled.")

            SESSION.add("assistant", result)
            save_task(
                command,
                json.dumps(task_plan),
                result,
            )
            return result

        except TaskCancelled:
            STATE.set("DONE", "interrupted")
            SESSION.add("assistant", "Cancelled.")
            return "Cancelled."

        except Exception as exc:
            STATE.set("ERROR", str(exc))
            return f"I couldn't complete that request: {exc}"

        finally:
            finish_task()
