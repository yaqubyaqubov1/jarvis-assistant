import json
import re

from ai.ollama import generate
from config import MAX_PLAN_STEPS
from tools.registry import tool_prompt


def _extract_json(text):
    fence = re.search(
        r"```(?:json)?\s*(.*?)```",
        text,
        re.S | re.I,
    )

    if fence:
        text = fence.group(1)

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        text = text[start : end + 1]

    return json.loads(text)


def plan(request):
    prompt = f"""
You are the task planner for J.A.R.V.I.S., a LOCAL Windows desktop agent.
Classify the request as either conversation or task.

GENERAL RULES
- Use ONLY tools listed below.
- Never invent shell, PowerShell, Python, or an unregistered tool.
- Never use unrestricted code execution.
- Prefer direct purpose-built tools over mouse/keyboard/screen automation.
- For greetings, casual conversation, explanations, or general knowledge,
  set kind="conversation" and steps=[].
- For an actual computer action, set kind="task".
- Maximum {MAX_PLAN_STEPS} top-level steps.
- Later steps may use "$last" as an argument value to insert the exact
  previous tool result.
- Later steps may use "$step1", "$step2", etc. inside string arguments.
- Potentially destructive tools are handled by the permission layer.
  Never try to bypass confirmation.
- Do not claim an action succeeded; executor/verifier decides that.

FILE RULES
- JARVIS may work with files and folders inside the user's Windows profile.
- Prefer file tools for file/folder operations instead of screen automation.
- Supported convenient roots include: home, desktop, documents, downloads,
  pictures, music, videos.
- If the user gives a known path such as "downloads/report.pdf", use it.
- If the exact path is unknown, use find_file first. find_file returns ONLY
  the best full path, so a later tool can safely use "$last".
- Use list_files to inspect a folder.
- Use read_document for document content.
- Use search_documents/semantic_search_documents for content searches.
- Use file_info for metadata.
- Use open_path to open a file/folder in Windows.
- Use create_folder, write_text_file, append_text_file for creation/writing.
- Use replace_text_in_file for targeted edits to an existing text/code file.
- Use copy_path for files OR folders.
- Use move_file, rename_file, delete_path only when the user actually asked
  for those changes; the permission layer will request confirmation.
- Example: "move my report from Downloads to Desktop" may be:
  1) find_file(query="report", root="downloads", kind="file")
  2) move_file(source="$last", destination="desktop")

SCREEN / GUI RULES
- JARVIS can inspect the primary display using local vision.
- Use describe_screen when the user only wants to know what is visible.
- Use click_screen_target when the user asks to click one clearly named
  visible control.
- Use screen_task for an adaptive multi-step GUI task where JARVIS must look
  again after each action.
- screen_task can click, double-click, type ordinary text, press keys,
  hotkeys, scroll, wait, and verify completion through repeated screenshots.
- Use screen_task only when a direct app/file/browser/system tool cannot do
  the job more reliably.
- Never route passwords, passcodes, OTPs, payment-card details, banking
  credentials, recovery codes, or other secrets through autonomous screen
  control.
- If the user asks to open a normal installed app, use open_application,
  not screen_task.
- If the user asks for a website, use open_website/open_url/browser tools,
  not screen_task unless interaction with an already visible webpage is the
  actual task.
- If the user says "look at my screen and ..." or "do this on my screen",
  screen_task is usually appropriate.

KEYBOARD RULES
- keyboard_type types into whichever application currently has focus.
- press_key and hotkey are for explicit keyboard actions.

REMINDERS
- For reminders, use set_reminder.
- For countdowns, use set_timer.

Return ONLY JSON in this exact shape:
{{
  "kind": "conversation",
  "response": "",
  "steps": [
    {{"tool": "tool_name", "arguments": {{}}}}
  ]
}}

TOOLS:
{tool_prompt()}

USER REQUEST:
{request}
""".strip()

    data = _extract_json(
        generate(
            prompt,
            temperature=0.05,
            num_predict=900,
        )
    )

    kind = str(
        data.get(
            "kind",
            "task",
        )
    ).lower()

    steps = data.get(
        "steps",
        [],
    )

    if not isinstance(
        steps,
        list,
    ):
        steps = []

    cleaned_steps = []

    for step in steps[:MAX_PLAN_STEPS]:
        if not isinstance(
            step,
            dict,
        ):
            continue

        tool = str(
            step.get(
                "tool",
                "",
            )
        ).strip()

        arguments = step.get(
            "arguments",
            {},
        )

        if not tool:
            continue

        if not isinstance(
            arguments,
            dict,
        ):
            arguments = {}

        cleaned_steps.append(
            {
                "tool": tool,
                "arguments": arguments,
            }
        )

    return {
        "kind": (
            "conversation"
            if kind == "conversation"
            else "task"
        ),
        "response": str(
            data.get(
                "response",
                "",
            )
        ),
        "steps": cleaned_steps,
    }
