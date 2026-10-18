import os
import shutil
import subprocess
import time
import webbrowser

from pathlib import Path

import psutil
import pyautogui
import pyperclip

from memory.database import (
    resolve_alias,
)

from tools.registry import (
    register,
)


# =========================================================
# KNOWN WINDOWS PROGRAMS
# =========================================================

KNOWN = {
    "calculator": [
        "calc.exe"
    ],

    "explorer": [
        "explorer.exe"
    ],

    "file explorer": [
        "explorer.exe"
    ],

    "task manager": [
        "taskmgr.exe"
    ],

    "terminal": [
        "cmd.exe"
    ],

    "command prompt": [
        "cmd.exe"
    ],
}


# =========================================================
# KNOWN WEBSITES
#
# These are only used when someone explicitly asks to
# open a known website as an application-like shortcut.
# =========================================================

SITES = {
    "youtube":
        "https://youtube.com",

    "google":
        "https://google.com",

    "github":
        "https://github.com",

    "gmail":
        "https://mail.google.com",

    "reddit":
        "https://reddit.com",
}


# =========================================================
# PROTECTED PROCESSES
# =========================================================

PROTECTED_PROCESS_NAMES = {
    "pycharm.exe",
    "pycharm64.exe",
    "idea.exe",
    "idea64.exe",

    "explorer.exe",

    "dwm.exe",
    "winlogon.exe",
    "csrss.exe",
    "services.exe",
    "lsass.exe",
    "smss.exe",
    "taskhostw.exe",
    "sihost.exe",

    "startmenuexperiencehost.exe",
    "shellexperiencehost.exe",
    "searchhost.exe",

    "applicationframehost.exe",
}


# =========================================================
# START MENU
# =========================================================

def _start_menu_roots():

    roots = []

    for variable in (
        "PROGRAMDATA",
        "APPDATA",
    ):

        value = os.environ.get(
            variable
        )

        if not value:
            continue

        roots.append(
            Path(value)
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
        )

    return roots


# =========================================================
# NOTEPAD++
# =========================================================

def _notepadpp():

    candidates = (
        Path(
            r"C:\Program Files\Notepad++"
            r"\notepad++.exe"
        ),

        Path(
            r"C:\Program Files (x86)"
            r"\Notepad++\notepad++.exe"
        ),
    )

    for path in candidates:

        if path.is_file():
            return path

    return None


# =========================================================
# PROCESS PROTECTION
# =========================================================

def _protected_process_ids():

    protected = {
        os.getpid()
    }

    try:

        process = psutil.Process(
            os.getpid()
        )

        while process is not None:

            protected.add(
                process.pid
            )

            process = (
                process.parent()
            )

    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied,
    ):
        pass

    return protected


def _is_protected_process(
    pid,
    process_name,
    window_title="",
):

    if pid in _protected_process_ids():
        return True

    process_name = (
        process_name
        or ""
    ).lower()

    window_title = (
        window_title
        or ""
    ).lower()

    if (
        process_name
        in PROTECTED_PROCESS_NAMES
    ):
        return True

    if (
        "pycharm"
        in process_name
        or
        "pycharm"
        in window_title
    ):
        return True

    return False


# =========================================================
# START MENU APPLICATION SEARCH
# =========================================================

def _find_start_menu_app(
    target,
):

    target = (
        str(target)
        .lower()
        .strip()
    )

    exact = []
    starts_with = []
    contains = []

    for root in _start_menu_roots():

        if not root.exists():
            continue

        try:

            links = root.rglob(
                "*.lnk"
            )

            for path in links:

                name = (
                    path.stem
                    .lower()
                    .strip()
                )

                if name == target:

                    exact.append(
                        path
                    )

                elif name.startswith(
                    target
                ):

                    starts_with.append(
                        path
                    )

                elif target in name:

                    contains.append(
                        path
                    )

        except OSError:
            continue

    if exact:
        return exact[0]

    if starts_with:
        return starts_with[0]

    if contains:
        return contains[0]

    return None


# =========================================================
# WINDOWS SEARCH
# =========================================================

def _windows_search_open_first_result(
    target,
):
    """
    Behave like the user pressing the Windows key,
    typing an application name and pressing Enter.

    This is useful for:
    - Microsoft Store apps
    - Steam games
    - UWP applications
    - applications without obvious executable paths
    """

    target = str(
        target
    ).strip()

    if not target:

        raise ValueError(
            "Search target is empty."
        )

    previous_clipboard = None
    clipboard_available = False

    try:

        previous_clipboard = (
            pyperclip.paste()
        )

        clipboard_available = True

    except Exception:
        pass

    # Open Windows Search / Start.
    pyautogui.press(
        "win"
    )

    time.sleep(
        0.55
    )

    # Clipboard paste handles spaces and unusual
    # characters much more reliably than typing.
    try:

        pyperclip.copy(
            target
        )

        pyautogui.hotkey(
            "ctrl",
            "v",
        )

    except Exception:

        pyautogui.write(
            target,
            interval=0.025,
        )

    # Give Windows Search time to rank results.
    time.sleep(
        1.15
    )

    # Open the first highlighted result.
    pyautogui.press(
        "enter"
    )

    time.sleep(
        0.35
    )

    if clipboard_available:

        try:

            pyperclip.copy(
                previous_clipboard
            )

        except Exception:
            pass

    return (
        f"Opened the first Windows Search "
        f"result for '{target}'."
    )


# =========================================================
# LIST APPLICATIONS
# =========================================================

@register(
    "list_applications",
    "List installed applications discoverable "
    "through the Windows Start Menu. "
    "arguments={query?}",
)
def list_applications(
    query="",
):

    query = (
        str(query)
        .lower()
        .strip()
    )

    names = []

    for root in _start_menu_roots():

        if not root.exists():
            continue

        try:

            for path in root.rglob(
                "*.lnk"
            ):

                if (
                    not query
                    or
                    query
                    in path.stem.lower()
                ):

                    names.append(
                        path.stem
                    )

        except OSError:
            continue

    names = sorted(
        set(names)
    )

    if not names:

        return (
            "No matching applications "
            "were found."
        )

    return "\n".join(
        names[:150]
    )


# =========================================================
# WINDOWS SEARCH TOOL
# =========================================================

@register(
    "windows_search_open",
    "Use Windows Search to find something and "
    "open the first result. Best for installed "
    "apps, games and Microsoft Store apps. "
    "arguments={query}",
)
def windows_search_open(
    query,
):

    return (
        _windows_search_open_first_result(
            query
        )
    )


# =========================================================
# OPEN APPLICATION
# =========================================================

@register(
    "open_application",
    "Open an installed Windows application or game. "
    "If JARVIS cannot resolve it directly, use Windows "
    "Search and open the first result. "
    "Do not use this for website requests. "
    "arguments={target}",
)
def open_application(
    target,
):

    original_target = str(
        target
    ).strip()

    if not original_target:

        return (
            "No application was specified."
        )

    target_text = (
        original_target
        .lower()
        .strip()
    )

    # ---------------------------------------------
    # ALIASES
    # ---------------------------------------------

    alias = resolve_alias(
        target_text
    )

    if alias:

        original_target = str(
            alias
        ).strip()

        target_text = (
            original_target
            .lower()
            .strip()
        )

    # ---------------------------------------------
    # NOTEPAD ALWAYS MEANS NOTEPAD++
    # ---------------------------------------------

    if target_text in {
        "notepad",
        "notepad++",
        "notepad plus plus",
    }:

        executable = (
            _notepadpp()
        )

        if executable:

            subprocess.Popen(
                [
                    str(executable)
                ],
                shell=False,
            )

            return (
                "Notepad++ is open, sir."
            )

        link = (
            _find_start_menu_app(
                "notepad++"
            )
        )

        if link:

            os.startfile(
                str(link)
            )

            return (
                "Notepad++ is open, sir."
            )

        return (
            "Notepad++ does not appear "
            "to be installed."
        )

    # ---------------------------------------------
    # KNOWN WINDOWS PROGRAM
    # ---------------------------------------------

    if target_text in KNOWN:

        subprocess.Popen(
            KNOWN[target_text],
            shell=False,
        )

        return (
            f"Opened {original_target}."
        )

    # ---------------------------------------------
    # KNOWN WEBSITE SHORTCUTS
    #
    # Kept for commands such as:
    # "open YouTube"
    #
    # Explicit "... website" requests are handled
    # by tools.web_tools instead.
    # ---------------------------------------------

    if target_text in SITES:

        webbrowser.open(
            SITES[target_text]
        )

        return (
            f"Opened {original_target}."
        )

    # ---------------------------------------------
    # COMMON EXECUTABLES
    # ---------------------------------------------

    common_executables = {
        "chrome":
            "chrome.exe",

        "google chrome":
            "chrome.exe",

        "edge":
            "msedge.exe",

        "microsoft edge":
            "msedge.exe",

        "spotify":
            "spotify.exe",

        "discord":
            "discord.exe",

        "pycharm":
            "pycharm64.exe",

        "visual studio code":
            "code.exe",

        "vs code":
            "code.exe",

        "vscode":
            "code.exe",
    }

    executable_name = (
        common_executables.get(
            target_text
        )
    )

    if executable_name:

        executable = shutil.which(
            executable_name
        )

        if executable:

            subprocess.Popen(
                [
                    executable
                ],
                shell=False,
            )

            return (
                f"Opened {original_target}."
            )

    # ---------------------------------------------
    # START MENU
    # ---------------------------------------------

    start_menu_result = (
        _find_start_menu_app(
            target_text
        )
    )

    if start_menu_result:

        os.startfile(
            str(start_menu_result)
        )

        return (
            f"Opened "
            f"{start_menu_result.stem}."
        )

    # ---------------------------------------------
    # WINDOWS SEARCH FALLBACK
    #
    # This is the important new behaviour.
    #
    # Example:
    # "Jarvis, open Geometry Dash"
    #
    # Windows key
    # -> Geometry Dash
    # -> Enter
    # ---------------------------------------------

    try:

        return (
            _windows_search_open_first_result(
                original_target
            )
        )

    except Exception as exc:

        return (
            "I couldn't launch "
            f"'{original_target}'. "
            f"Windows Search also failed: {exc}"
        )


# =========================================================
# CLOSE APPLICATION
# =========================================================

@register(
    "close_application",
    "Close a named application. "
    "PyCharm and JARVIS are protected. "
    "Confirmation required. "
    "arguments={target}",
)
def close_application(
    target,
):

    target_text = (
        str(target)
        .lower()
        .replace(
            ".exe",
            "",
        )
        .strip()
    )

    if (
        "pycharm"
        in target_text
    ):

        return (
            "I won't close PyCharm while "
            "it is hosting JARVIS."
        )

    aliases = {
        "notepad":
            "notepad++",

        "notepad++":
            "notepad++",

        "edge":
            "msedge",

        "google chrome":
            "chrome",

        "chrome":
            "chrome",

        "discord":
            "discord",

        "spotify":
            "spotify",

        "visual studio code":
            "code",

        "vs code":
            "code",

        "vscode":
            "code",
    }

    needle = aliases.get(
        target_text,
        target_text,
    )

    protected_pids = (
        _protected_process_ids()
    )

    closed = []

    for process in psutil.process_iter(
        [
            "pid",
            "name",
        ]
    ):

        pid = (
            process.info
            .get("pid")
        )

        if pid in protected_pids:
            continue

        name = (
            process.info
            .get(
                "name"
            )
            or ""
        ).lower()

        if (
            name
            in PROTECTED_PROCESS_NAMES
        ):
            continue

        if (
            "pycharm"
            in name
        ):
            continue

        normalized_name = (
            name.replace(
                ".exe",
                "",
            )
        )

        if (
            normalized_name == needle
            or
            needle in normalized_name
        ):

            try:

                process.terminate()

                closed.append(
                    process.info.get(
                        "name"
                    )
                    or name
                )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
            ):
                continue

    if closed:

        return (
            "Closed: "
            + ", ".join(
                closed
            )
        )

    return (
        "No running process matched "
        f"'{target}'."
    )


# =========================================================
# CLOSE ALL APPLICATIONS
# =========================================================

@register(
    "close_all_apps",
    "Gracefully close visible user applications "
    "except PyCharm, JARVIS and Windows Explorer. "
    "Confirmation required. arguments={}",
)
def close_all_apps():

    try:

        import win32con
        import win32gui
        import win32process

    except ImportError as exc:

        raise RuntimeError(
            "close_all_apps requires pywin32."
        ) from exc

    protected_pids = (
        _protected_process_ids()
    )

    closed_windows = []

    seen = set()

    def callback(
        hwnd,
        _,
    ):

        if hwnd in seen:
            return

        seen.add(
            hwnd
        )

        if not (
            win32gui.IsWindowVisible(
                hwnd
            )
        ):
            return

        title = (
            win32gui.GetWindowText(
                hwnd
            )
            or ""
        ).strip()

        if not title:
            return

        try:

            class_name = (
                win32gui.GetClassName(
                    hwnd
                )
                or ""
            )

        except Exception:

            class_name = ""

        if class_name in {
            "Progman",
            "WorkerW",
            "Shell_TrayWnd",
            "Shell_SecondaryTrayWnd",
        }:
            return

        try:

            _, pid = (
                win32process
                .GetWindowThreadProcessId(
                    hwnd
                )
            )

        except Exception:
            return

        if pid in protected_pids:
            return

        try:

            process = (
                psutil.Process(
                    pid
                )
            )

            process_name = (
                process.name()
                or ""
            ).lower()

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
        ):
            return

        if _is_protected_process(
            pid,
            process_name,
            title,
        ):
            return

        try:

            win32gui.PostMessage(
                hwnd,
                win32con.WM_CLOSE,
                0,
                0,
            )

            closed_windows.append(
                title
            )

        except Exception:
            pass

    win32gui.EnumWindows(
        callback,
        None,
    )

    time.sleep(
        0.75
    )

    if not closed_windows:

        return (
            "There were no other visible "
            "applications to close, sir."
        )

    return (
        f"Closed {len(closed_windows)} "
        f"application window(s). "
        f"PyCharm and JARVIS remain running."
    )


# =========================================================
# WINDOWS
# =========================================================

@register(
    "list_windows",
    "List visible Windows application windows. "
    "arguments={}",
)
def list_windows():

    try:

        import win32gui

        titles = []

        def callback(
            hwnd,
            _,
        ):

            if not (
                win32gui.IsWindowVisible(
                    hwnd
                )
            ):
                return

            title = (
                win32gui.GetWindowText(
                    hwnd
                )
                or ""
            ).strip()

            if title:

                titles.append(
                    title
                )

        win32gui.EnumWindows(
            callback,
            None,
        )

        return (
            "\n".join(
                titles[:150]
            )
            or
            "No titled windows found."
        )

    except Exception as exc:

        return (
            "Window listing unavailable: "
            f"{exc}"
        )


@register(
    "get_active_window",
    "Get the title of the currently active "
    "Windows window. arguments={}",
)
def get_active_window():

    try:

        import win32gui

        hwnd = (
            win32gui.GetForegroundWindow()
        )

        if not hwnd:

            return (
                "No active window."
            )

        title = (
            win32gui.GetWindowText(
                hwnd
            )
            or ""
        ).strip()

        return (
            title
            or
            "Active window has no title."
        )

    except Exception as exc:

        return (
            "Active window unavailable: "
            f"{exc}"
        )