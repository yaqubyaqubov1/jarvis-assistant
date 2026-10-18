import re


CONVERSATION_EXACT = {
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "how are you doing",
    "what's up",
    "whats up",
    "thanks",
    "thank you",
    "who are you",
    "what are you",
}


def looks_conversational(text):
    query = str(text).lower().strip().rstrip(".!?")

    if query in CONVERSATION_EXACT:
        return True

    prefixes = (
        "explain ",
        "tell me about ",
        "what is ",
        "what are ",
        "who is ",
        "who was ",
        "why ",
        "how does ",
        "how do ",
        "can you explain ",
        "define ",
        "give me an example of ",
    )

    return query.startswith(prefixes)


def _clean_raw(text):
    raw = str(text).strip().rstrip(".!?").strip()
    raw = re.sub(r"^please\s+", "", raw, flags=re.I)
    raw = re.sub(r"\s+please$", "", raw, flags=re.I)
    return raw


def _clean_website_target(target):
    target = str(target).strip()
    target = re.sub(r"(?:'s|’s)$", "", target, flags=re.I)
    return target.strip()


def _strip_matching_quotes(text):
    text = str(text).strip()

    pairs = (
        ('"', '"'),
        ("'", "'"),
        ("“", "”"),
        ("‘", "’"),
    )

    for start, end in pairs:
        if len(text) >= 2 and text.startswith(start) and text.endswith(end):
            return text[1:-1]

    return text


def quick_plan(text):
    raw = _clean_raw(text)
    command = raw.lower()

    # =====================================================
    # KEYBOARD TYPING
    #
    # Examples:
    #   type Hello in my keyboard
    #   type Hello
    #   type "Hello world" and press enter
    # =====================================================

    type_match = re.fullmatch(
        r"type\s+(.+?)"
        r"(?:\s+(?:in|on)\s+(?:my\s+)?keyboard)?"
        r"(?:\s+and\s+press\s+enter)?",
        raw,
        flags=re.I,
    )

    if type_match:
        content = _strip_matching_quotes(type_match.group(1))
        press_enter = bool(
            re.search(
                r"\s+and\s+press\s+enter$",
                raw,
                flags=re.I,
            )
        )

        return {
            "kind": "task",
            "response": "",
            "steps": [
                {
                    "tool": "keyboard_type",
                    "arguments": {
                        "text": content,
                        "press_enter": press_enter,
                    },
                }
            ],
        }

    # =====================================================
    # CLOSE EVERYTHING
    # =====================================================

    if command in {
        "close everything",
        "close all applications",
        "close all apps",
        "close everything except pycharm",
        "close all apps except pycharm",
        "close all applications except pycharm",
    }:
        return {
            "kind": "task",
            "response": "",
            "steps": [
                {
                    "tool": "close_all_apps",
                    "arguments": {},
                }
            ],
        }

    # =====================================================
    # EXPLICIT URL
    # =====================================================

    explicit_url = re.fullmatch(
        r"(?:open|go to)\s+"
        r"(https?://\S+|(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/\S*)?)",
        command,
        flags=re.I,
    )

    if explicit_url:
        return {
            "kind": "task",
            "response": "",
            "steps": [
                {
                    "tool": "open_url",
                    "arguments": {
                        "url": explicit_url.group(1),
                    },
                }
            ],
        }

    # =====================================================
    # WEBSITE REQUEST
    # =====================================================

    website_patterns = (
        r"(?:open|visit|go to)\s+(?:the\s+)?(.+?)(?:'s|’s)?\s+(?:website|site|webpage|page)",
        r"(?:open|visit|go to)\s+(?:the\s+)?(?:website|site|webpage|page)\s+(?:for|of)\s+(.+)",
    )

    for pattern in website_patterns:
        match = re.fullmatch(pattern, raw, flags=re.I)

        if match:
            target = _clean_website_target(match.group(1))
            return {
                "kind": "task",
                "response": "",
                "steps": [
                    {
                        "tool": "open_website",
                        "arguments": {
                            "query": target,
                        },
                    }
                ],
            }

    # =====================================================
    # WEB SEARCH
    # =====================================================

    search_match = re.fullmatch(
        r"(?:search(?:\s+the\s+web)?\s+for|look\s+up|google|duckduckgo)\s+(.+)",
        raw,
        flags=re.I,
    )

    if search_match:
        return {
            "kind": "task",
            "response": "",
            "steps": [
                {
                    "tool": "web_search",
                    "arguments": {
                        "query": search_match.group(1).strip(),
                    },
                }
            ],
        }

    # =====================================================
    # GENERIC APP OPEN / LAUNCH
    # =====================================================

    open_match = re.fullmatch(
        r"(?:open|launch|start|run)\s+(?:the\s+)?(.+)",
        raw,
        flags=re.I,
    )

    if open_match:
        target = open_match.group(1).strip()
        lower_target = target.lower()

        if not any(
            lower_target.endswith(word)
            for word in (
                " website",
                " site",
                " webpage",
                " web page",
            )
        ):
            return {
                "kind": "task",
                "response": "",
                "steps": [
                    {
                        "tool": "open_application",
                        "arguments": {
                            "target": target,
                        },
                    }
                ],
            }

    # =====================================================
    # CLOSE APPLICATION
    # =====================================================

    close_match = re.fullmatch(
        r"close\s+(?:the\s+)?(.+)",
        raw,
        flags=re.I,
    )

    if close_match:
        target = close_match.group(1).strip()

        if target.lower() not in {
            "everything",
            "all apps",
            "all applications",
        }:
            return {
                "kind": "task",
                "response": "",
                "steps": [
                    {
                        "tool": "close_application",
                        "arguments": {
                            "target": target,
                        },
                    }
                ],
            }

    # =====================================================
    # TIME / DATE
    # =====================================================

    if command in {
        "what time is it",
        "what's the time",
        "tell me the time",
        "time",
        "what date is it",
        "what's the date",
        "tell me the date",
    }:
        return {
            "kind": "task",
            "response": "",
            "steps": [
                {
                    "tool": "get_time_date",
                    "arguments": {},
                }
            ],
        }

    # =====================================================
    # QUICK CONTROLS
    # =====================================================

    controls = {
        "volume up": "volume_up",
        "turn volume up": "volume_up",
        "volume down": "volume_down",
        "turn volume down": "volume_down",
        "mute": "volume_mute",
        "mute volume": "volume_mute",
        "pause music": "media_play_pause",
        "play music": "media_play_pause",
        "next song": "media_next",
        "previous song": "media_previous",
        "take a screenshot": "take_screenshot",
        "take screenshot": "take_screenshot",
    }

    if command in controls:
        return {
            "kind": "task",
            "response": "",
            "steps": [
                {
                    "tool": controls[command],
                    "arguments": {},
                }
            ],
        }

    return None
