AUTO = "auto"
CONFIRM = "confirm"
BLOCK = "block"


POLICY = {
    # Read-only / safe
    "get_time_date": AUTO,
    "system_diagnostics": AUTO,
    "list_files": AUTO,
    "search_files": AUTO,
    "find_file": AUTO,
    "file_info": AUTO,
    "open_path": AUTO,
    "read_document": AUTO,
    "search_documents": AUTO,
    "semantic_search_documents": AUTO,
    "ask_documents": AUTO,
    "read_clipboard": AUTO,
    "take_screenshot": AUTO,
    "describe_screen": AUTO,
    "click_screen_target": AUTO,
    "screen_task": AUTO,
    "user_idle_time": AUTO,
    "list_windows": AUTO,
    "get_active_window": AUTO,
    "list_applications": AUTO,
    "list_reminders": AUTO,
    "list_timers": AUTO,
    "recall": AUTO,
    "get_preference": AUTO,
    "list_preferences": AUTO,
    "list_aliases": AUTO,
    "task_history": AUTO,

    # Apps
    "open_application": AUTO,
    "windows_search_open": AUTO,
    "close_application": CONFIRM,
    "close_all_apps": CONFIRM,

    # Internet / browser
    "open_url": AUTO,
    "open_website": AUTO,
    "web_search": AUTO,
    "web_news_search": AUTO,
    "read_webpage": AUTO,
    "browser_search": AUTO,
    "browser_open": AUTO,
    "browser_read": AUTO,
    "browser_current_page": AUTO,
    "browser_back": AUTO,
    "browser_forward": AUTO,
    "browser_new_tab": AUTO,
    "browser_close_tab": AUTO,
    "browser_click_text": AUTO,
    "browser_fill": AUTO,
    "browser_press": CONFIRM,
    "download_file": CONFIRM,
    "browser_download_click": CONFIRM,

    # Desktop / keyboard / mouse
    "volume_up": AUTO,
    "volume_down": AUTO,
    "volume_mute": AUTO,
    "media_play_pause": AUTO,
    "media_next": AUTO,
    "media_previous": AUTO,
    "keyboard_type": AUTO,
    "press_key": AUTO,
    "hotkey": AUTO,
    "mouse_click": AUTO,
    "mouse_move": AUTO,
    "mouse_scroll": AUTO,
    "write_clipboard": AUTO,

    # Files
    "create_folder": AUTO,
    "write_text_file": AUTO,
    "append_text_file": AUTO,
    "replace_text_in_file": CONFIRM,
    "copy_file": AUTO,
    "copy_path": AUTO,
    "zip_path": AUTO,
    "unzip_archive": AUTO,
    "move_file": CONFIRM,
    "rename_file": CONFIRM,
    "delete_path": CONFIRM,

    # Reminders / memory / modes
    "set_reminder": AUTO,
    "set_timer": AUTO,
    "cancel_reminder": AUTO,
    "snooze_reminder": AUTO,
    "remember": AUTO,
    "set_preference": AUTO,
    "set_alias": AUTO,
    "activate_mode": AUTO,
    "configure_mode": AUTO,
    "local_answer": AUTO,

    # System
    "lock_pc": CONFIRM,
    "power_action": CONFIRM,
    "set_wifi": CONFIRM,
    "set_brightness": AUTO,

    # Never expose unrestricted code execution to the model
    "raw_shell": BLOCK,
    "raw_powershell": BLOCK,
    "raw_python": BLOCK,
}


SENSITIVE_BROWSER_ACTIONS = {
    "buy",
    "purchase",
    "checkout",
    "place order",
    "pay",
    "subscribe",
    "unsubscribe",
    "delete",
    "remove account",
    "close account",
    "transfer",
    "send money",
    "confirm payment",
    "publish",
    "post",
    "send",
}


SENSITIVE_FIELDS = {
    "password",
    "passcode",
    "credit card",
    "card number",
    "cvv",
    "cvc",
    "security code",
    "otp",
    "verification code",
    "bank account",
    "routing number",
    "social security",
    "ssn",
}


SCREEN_CONFIRM_ACTIONS = {
    "delete",
    "remove",
    "erase",
    "uninstall",
    "install",
    "purchase",
    "buy",
    "checkout",
    "pay",
    "transfer",
    "send",
    "submit",
    "publish",
    "post",
    "upload",
    "restart",
    "shutdown",
    "sleep computer",
    "format",
    "factory reset",
    "change system setting",
    "change windows setting",
    "close account",
    "remove account",
}


SCREEN_BLOCKED_SECRET_ACTIONS = {
    "password",
    "passcode",
    "one-time password",
    "one time password",
    "otp",
    "verification code",
    "security code",
    "recovery code",
    "credit card",
    "card number",
    "cvv",
    "cvc",
    "bank account",
    "routing number",
    "social security",
    "ssn",
}


def permission_for(
    tool_name,
    arguments=None,
):
    level = POLICY.get(
        tool_name,
        BLOCK,
    )

    arguments = (
        arguments
        if isinstance(
            arguments,
            dict,
        )
        else {}
    )

    if tool_name == "browser_click_text":
        text = str(
            arguments.get(
                "text",
                "",
            )
        ).lower()

        if any(
            phrase in text
            for phrase in SENSITIVE_BROWSER_ACTIONS
        ):
            return CONFIRM

    if tool_name == "browser_fill":
        field = str(
            arguments.get(
                "field",
                "",
            )
        ).lower()

        if any(
            phrase in field
            for phrase in SENSITIVE_FIELDS
        ):
            return CONFIRM

    if tool_name == "screen_task":
        instruction = str(
            arguments.get(
                "instruction",
                "",
            )
        ).lower()

        if any(
            phrase in instruction
            for phrase in SCREEN_BLOCKED_SECRET_ACTIONS
        ):
            return BLOCK

        if any(
            phrase in instruction
            for phrase in SCREEN_CONFIRM_ACTIONS
        ):
            return CONFIRM

    return level
