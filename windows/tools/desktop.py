import datetime as dt
import json
import math
import re
import time
from pathlib import Path

import psutil
import pyautogui
import pyperclip

from config import DATA_DIR
from core.cancellation import checkpoint
from tools.registry import register


pyautogui.FAILSAFE = True


# =========================================================
# BASIC SYSTEM INFORMATION
# =========================================================

@register(
    "get_time_date",
    "Get current local date and time. arguments={}",
)
def get_time_date():
    return dt.datetime.now().strftime(
        "%A, %B %d, %Y at %I:%M %p"
    )


@register(
    "system_diagnostics",
    "Get CPU, RAM, battery and disk usage. arguments={}",
)
def system_diagnostics():
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(
        str(Path.home().anchor)
    )
    battery = psutil.sensors_battery()

    battery_text = (
        f" Battery {battery.percent:.0f}%."
        if battery
        else ""
    )

    return (
        f"CPU {psutil.cpu_percent(0.25):.0f}%. "
        f"RAM {memory.percent:.0f}%. "
        f"Disk {disk.percent:.0f}%."
        f"{battery_text}"
    )


# =========================================================
# CLIPBOARD
# =========================================================

@register(
    "read_clipboard",
    "Read clipboard text. arguments={}",
)
def read_clipboard():
    return str(
        pyperclip.paste()
    )[:20000]


@register(
    "write_clipboard",
    "Put text on clipboard. arguments={text}",
)
def write_clipboard(text):
    pyperclip.copy(
        str(text)
    )
    return "Clipboard updated."


# =========================================================
# MEDIA / VOLUME
# =========================================================

@register(
    "volume_up",
    "Increase system volume. arguments={}",
)
def volume_up():
    pyautogui.press(
        "volumeup"
    )
    return "Volume increased."


@register(
    "volume_down",
    "Decrease system volume. arguments={}",
)
def volume_down():
    pyautogui.press(
        "volumedown"
    )
    return "Volume decreased."


@register(
    "volume_mute",
    "Toggle mute. arguments={}",
)
def volume_mute():
    pyautogui.press(
        "volumemute"
    )
    return "Mute toggled."


@register(
    "media_play_pause",
    "Play or pause media. arguments={}",
)
def media_play_pause():
    pyautogui.press(
        "playpause"
    )
    return "Play/pause toggled."


@register(
    "media_next",
    "Go to the next media track. arguments={}",
)
def media_next():
    pyautogui.press(
        "nexttrack"
    )
    return "Next track."


@register(
    "media_previous",
    "Go to the previous media track. arguments={}",
)
def media_previous():
    pyautogui.press(
        "prevtrack"
    )
    return "Previous track."


# =========================================================
# KEYBOARD
# =========================================================

def _type_one_line(
    text,
    interval,
):
    text = str(text)

    try:
        text.encode("ascii")

        pyautogui.write(
            text,
            interval=float(interval),
        )
        return

    except UnicodeEncodeError:
        pass

    old_clipboard = None
    had_clipboard = False

    try:
        old_clipboard = pyperclip.paste()
        had_clipboard = True
    except Exception:
        pass

    pyperclip.copy(text)
    pyautogui.hotkey(
        "ctrl",
        "v",
    )
    time.sleep(0.06)

    if had_clipboard:
        try:
            pyperclip.copy(
                old_clipboard
            )
        except Exception:
            pass


def _interruptible_sleep(seconds):
    seconds = max(
        0.0,
        float(seconds),
    )

    end = time.monotonic() + seconds

    while time.monotonic() < end:
        checkpoint()
        time.sleep(
            min(
                0.1,
                max(0.0, end - time.monotonic()),
            )
        )

    checkpoint()


@register(
    "keyboard_type",
    "Type text into the currently focused window using the keyboard. "
    "Can optionally press Enter afterwards. "
    "arguments={text,press_enter?,interval?}",
)
def keyboard_type(
    text,
    press_enter=False,
    interval=0.018,
):
    checkpoint()

    text = str(text)

    _interruptible_sleep(
        0.15
    )

    lines = text.split("\n")

    for index, line in enumerate(lines):
        checkpoint()
        _type_one_line(
            line,
            interval,
        )

        if index < len(lines) - 1:
            pyautogui.press(
                "enter"
            )

    if bool(press_enter):
        checkpoint()
        pyautogui.press(
            "enter"
        )

    return "Text typed."


@register(
    "press_key",
    "Press a keyboard key. arguments={key}",
)
def press_key(key):
    checkpoint()
    pyautogui.press(
        str(key)
    )
    return f"Pressed {key}."


@register(
    "hotkey",
    "Press a keyboard shortcut. arguments={keys:[...]}",
)
def hotkey(keys):
    checkpoint()

    key_list = [
        str(item)
        for item in keys
    ]

    if not key_list:
        raise ValueError(
            "No hotkey keys were supplied."
        )

    if len(key_list) > 6:
        raise ValueError(
            "Too many keys in one hotkey."
        )

    pyautogui.hotkey(
        *key_list
    )

    return "Hotkey pressed."


# =========================================================
# MOUSE
# =========================================================

@register(
    "mouse_move",
    "Move the mouse pointer. arguments={x,y,duration?}",
)
def mouse_move(
    x,
    y,
    duration=0.2,
):
    checkpoint()

    pyautogui.moveTo(
        int(x),
        int(y),
        duration=float(duration),
    )

    return "Mouse moved."


@register(
    "mouse_click",
    "Click the mouse. arguments={x?,y?,button?,clicks?}",
)
def mouse_click(
    x=None,
    y=None,
    button="left",
    clicks=1,
):
    checkpoint()

    pyautogui.click(
        x=None if x is None else int(x),
        y=None if y is None else int(y),
        button=str(button),
        clicks=max(1, min(int(clicks), 3)),
    )

    return "Clicked."


@register(
    "mouse_scroll",
    "Scroll the active window. Positive scrolls up, negative scrolls down. "
    "arguments={amount}",
)
def mouse_scroll(amount):
    checkpoint()

    amount = max(
        -3000,
        min(
            int(amount),
            3000,
        ),
    )

    pyautogui.scroll(
        amount
    )

    return "Scrolled."


# =========================================================
# SCREENSHOT
# =========================================================

@register(
    "take_screenshot",
    "Save a screenshot of the primary display locally. arguments={filename?}",
)
def take_screenshot(
    filename="screenshot.png",
):
    checkpoint()

    folder = (
        DATA_DIR
        / "screenshots"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        folder
        / Path(str(filename)).name
    )

    if path.suffix.lower() != ".png":
        path = path.with_suffix(
            ".png"
        )

    pyautogui.screenshot(
        str(path)
    )

    checkpoint()

    return str(path)


# =========================================================
# SCREEN UNDERSTANDING
# =========================================================

@register(
    "describe_screen",
    "Look at the current primary display using the local Ollama vision "
    "model and answer a question about what is visible. arguments={question?}",
)
def describe_screen(
    question=(
        "Describe the screen and mention any visible error, dialog, "
        "application, important control, or text relevant to the user."
    ),
):
    from ai.ollama import describe_image

    checkpoint()

    path = take_screenshot(
        "screen_for_vision.png"
    )

    result = describe_image(
        path,
        str(question),
    )

    checkpoint()

    return result


def _extract_json_object(raw):
    text = str(raw).strip()

    fence = re.search(
        r"```(?:json)?\s*(.*?)```",
        text,
        re.S | re.I,
    )

    if fence:
        text = fence.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start < 0 or end <= start:
        raise ValueError(
            "Vision did not return a JSON action."
        )

    return json.loads(
        text[start : end + 1]
    )


def _validate_xy(
    x,
    y,
    width,
    height,
):
    x = int(x)
    y = int(y)

    if not (
        0 <= x < width
        and 0 <= y < height
    ):
        raise ValueError(
            "Vision returned coordinates outside the screen."
        )

    return x, y


@register(
    "click_screen_target",
    "Look at the screen with the local vision model, locate a visible UI "
    "target, and click it. arguments={target}",
)
def click_screen_target(target):
    from PIL import Image
    from ai.ollama import describe_image

    checkpoint()

    path = take_screenshot(
        "screen_for_click.png"
    )

    with Image.open(path) as image:
        width, height = image.size

    prompt = f"""
Find the visible UI element described as: {target}

The screenshot size is exactly {width}x{height} pixels.
Return ONLY JSON with this shape:
{{
  "found": true,
  "x": 123,
  "y": 456,
  "description": "what you found"
}}

If the requested element is not clearly visible, return:
{{
  "found": false,
  "x": 0,
  "y": 0,
  "description": "not found"
}}

Coordinates must be pixel coordinates in this exact screenshot.
Do not guess if the target is ambiguous.
""".strip()

    raw = describe_image(
        path,
        prompt,
    )

    checkpoint()

    data = _extract_json_object(
        raw
    )

    if not data.get("found"):
        return f"I could not find '{target}' on screen."

    x, y = _validate_xy(
        data.get("x", 0),
        data.get("y", 0),
        width,
        height,
    )

    pyautogui.click(
        x,
        y,
    )

    checkpoint()

    return f"Clicked {target} at ({x}, {y})."


# =========================================================
# ADAPTIVE SCREEN TASK
# =========================================================

_BLOCKED_SCREEN_SECRET_WORDS = {
    "password",
    "passcode",
    "pin code",
    "one-time password",
    "one time password",
    "otp",
    "cvv",
    "cvc",
    "credit card",
    "card number",
    "bank account",
    "routing number",
    "social security",
    "ssn",
    "recovery code",
    "security code",
}


@register(
    "screen_task",
    "Use the local vision model to repeatedly inspect the primary display "
    "and perform a safe multi-step UI task by clicking, typing, pressing "
    "keys, using hotkeys, scrolling, and waiting. The task remains fully "
    "interruptible. Do not use this when a direct app/file/browser tool is "
    "available. arguments={instruction,max_steps?}",
)
def screen_task(
    instruction,
    max_steps=8,
):
    from PIL import Image
    from ai.ollama import describe_image

    checkpoint()

    instruction = str(
        instruction
    ).strip()

    if not instruction:
        raise ValueError(
            "Screen task instruction is empty."
        )

    lowered_instruction = (
        instruction.lower()
    )

    if any(
        phrase in lowered_instruction
        for phrase in _BLOCKED_SCREEN_SECRET_WORDS
    ):
        return (
            "I won't enter or handle passwords, verification codes, "
            "payment-card details, banking credentials, or other secrets "
            "through autonomous screen control."
        )

    max_steps = max(
        1,
        min(
            int(max_steps),
            12,
        ),
    )

    action_history = []

    for step_number in range(
        1,
        max_steps + 1,
    ):
        checkpoint()

        screenshot = take_screenshot(
            f"screen_task_{step_number}.png"
        )

        with Image.open(screenshot) as image:
            width, height = image.size

        history_text = (
            "\n".join(
                f"- {item}"
                for item in action_history[-6:]
            )
            or "- none yet"
        )

        prompt = f"""
You are the visual-control component of a LOCAL Windows desktop assistant.

USER TASK:
{instruction}

CURRENT SCREENSHOT:
{width}x{height} pixels

PREVIOUS ACTIONS:
{history_text}

Choose EXACTLY ONE next action based only on what is visibly on screen.
Return ONLY one JSON object using this schema:
{{
  "action": "click|double_click|type|press|hotkey|scroll|wait|done|fail",
  "x": 0,
  "y": 0,
  "text": "",
  "key": "",
  "keys": [],
  "amount": 0,
  "seconds": 0.0,
  "description": "short explanation"
}}

Rules:
- Use click/double_click only when the target is clearly visible.
- x/y are exact screenshot pixel coordinates.
- Use type only for ordinary non-secret text.
- Never type or reveal passwords, passcodes, OTPs, payment-card data,
  banking credentials, recovery codes, or other secrets.
- If a password/security/payment field is required, return action="fail".
- Do not approve an unexpected destructive, purchase, payment, upload,
  publish, send, uninstall, format, shutdown, restart, or account-removal
  confirmation unless that action is explicitly part of the user's task.
- If the requested task is visibly complete, return action="done".
- If you cannot safely determine the next action, return action="fail".
- Do not invent controls that are not visible.
""".strip()

        raw = describe_image(
            screenshot,
            prompt,
        )

        checkpoint()

        try:
            action = _extract_json_object(
                raw
            )
        except Exception as exc:
            return (
                "I could see the screen, but the local vision model did "
                f"not return a usable action: {exc}"
            )

        action_name = str(
            action.get("action", "")
        ).strip().lower()

        description = str(
            action.get("description", "")
        ).strip()

        if action_name == "done":
            if description:
                return f"Screen task completed. {description}"

            return "Screen task completed."

        if action_name == "fail":
            return (
                description
                or "I could not safely determine the next screen action."
            )

        if action_name == "click":
            x, y = _validate_xy(
                action.get("x", 0),
                action.get("y", 0),
                width,
                height,
            )

            pyautogui.click(
                x,
                y,
            )

            action_history.append(
                description
                or f"clicked ({x}, {y})"
            )

        elif action_name == "double_click":
            x, y = _validate_xy(
                action.get("x", 0),
                action.get("y", 0),
                width,
                height,
            )

            pyautogui.doubleClick(
                x,
                y,
                interval=0.12,
            )

            action_history.append(
                description
                or f"double-clicked ({x}, {y})"
            )

        elif action_name == "type":
            text = str(
                action.get("text", "")
            )

            lowered_text = text.lower()

            if any(
                phrase in lowered_text
                for phrase in _BLOCKED_SCREEN_SECRET_WORDS
            ):
                return (
                    "I stopped because the requested screen action appears "
                    "to involve sensitive credentials or secrets."
                )

            keyboard_type(
                text,
                press_enter=False,
            )

            action_history.append(
                description
                or "typed text"
            )

        elif action_name == "press":
            key = str(
                action.get("key", "")
            ).strip()

            if not key:
                return "Vision requested a key press without specifying a key."

            pyautogui.press(
                key
            )

            action_history.append(
                description
                or f"pressed {key}"
            )

        elif action_name == "hotkey":
            keys = action.get(
                "keys",
                [],
            )

            if not isinstance(keys, list):
                return "Vision returned an invalid hotkey."

            keys = [
                str(key).strip()
                for key in keys
                if str(key).strip()
            ][:6]

            if not keys:
                return "Vision requested a hotkey without specifying keys."

            pyautogui.hotkey(
                *keys
            )

            action_history.append(
                description
                or f"pressed {'+'.join(keys)}"
            )

        elif action_name == "scroll":
            amount = int(
                action.get(
                    "amount",
                    0,
                )
            )

            amount = max(
                -3000,
                min(
                    amount,
                    3000,
                ),
            )

            pyautogui.scroll(
                amount
            )

            action_history.append(
                description
                or f"scrolled {amount}"
            )

        elif action_name == "wait":
            seconds = float(
                action.get(
                    "seconds",
                    1.0,
                )
            )

            seconds = max(
                0.1,
                min(
                    seconds,
                    5.0,
                ),
            )

            _interruptible_sleep(
                seconds
            )

            action_history.append(
                description
                or f"waited {seconds:.1f}s"
            )

        else:
            return (
                "The local vision model returned an unsupported "
                f"screen action: {action_name or '[empty]'}"
            )

        checkpoint()

        # Give the UI enough time to react before the next screenshot.
        _interruptible_sleep(
            0.55
        )

    return (
        "I reached the screen-task step limit before the local vision "
        "model could verify completion."
    )


# =========================================================
# IDLE TIME
# =========================================================

@register(
    "user_idle_time",
    "Get seconds since the user's last keyboard or mouse input. arguments={}",
)
def user_idle_time():
    import ctypes

    class LASTINPUTINFO(
        ctypes.Structure
    ):
        _fields_ = [
            (
                "cbSize",
                ctypes.c_uint,
            ),
            (
                "dwTime",
                ctypes.c_uint,
            ),
        ]

    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(
        info
    )

    if not (
        ctypes.windll.user32.GetLastInputInfo(
            ctypes.byref(info)
        )
    ):
        return "Idle time unavailable."

    millis = (
        ctypes.windll.kernel32.GetTickCount()
        - info.dwTime
    )

    return (
        f"{millis / 1000.0:.1f} seconds idle."
    )
