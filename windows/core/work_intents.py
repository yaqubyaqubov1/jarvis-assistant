"""Deterministic fast routing for work files, Gmail, and account pages.

Keep the rules intentionally conservative: no guessed recipients, filenames,
columns, or destructive actions. More complex documents use a focused planner.
"""
import re


def _task(tool, arguments=None):
    return {"kind": "task", "response": "", "steps": [
        {"tool": tool, "arguments": arguments or {}}
    ]}


def _reply(message):
    return {"kind": "conversation", "response": message, "steps": []}


def _clean(text):
    text = str(text).strip().rstrip(".!?")
    text = re.sub(r"^please\s+", "", text, flags=re.I)
    text = re.sub(r"\s+please$", "", text, flags=re.I)
    return text.strip()


def _has(text, expression):
    return bool(re.search(expression, text, flags=re.I))


def _split_items(text):
    text = re.sub(r"\s+\band\b\s+", ", ", str(text).strip(), flags=re.I)
    return [x.strip(" ,;:'\"") for x in re.split(r"\s*,\s*|\s*;\s*", text) if x.strip(" ,;:'\"")]


def _numeric(value):
    value = str(value).strip()
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def _filename(text, suffix):
    # Extract only an explicit filename; never invent a path from an account
    # or email address. Default location is the user's Documents directory.
    match = re.search(
        r'\b(?:called|named|name|as|file)\s+["“]?'
        r'([a-zA-Z0-9][\w .-]{0,90}\.' + suffix + r')\b',
        text, flags=re.I,
    )
    if not match:
        match = re.search(
            r'\b([a-zA-Z0-9][\w.-]{0,90}\.' + suffix + r')\b',
            text, flags=re.I,
        )
    if not match:
        return None
    name = match.group(1).strip()
    if "/" in name or "\\" in name or name.startswith("."):
        return None
    # The filename is treated as a leaf, with no slashes or traversal.
    if ".." in name:
        return None
    folder = "documents"
    if _has(text, r"\b(?:on|to|in|under)\s+(?:my\s+)?desktop\b"):
        folder = "desktop"
    elif _has(text, r"\b(?:to|in|under)\s+(?:my\s+)?downloads\b"):
        folder = "downloads"
    return folder + "/" + name


def _sheet_data(text, path):
    columns_match = re.search(
        r"\bcolumns?\s+(?:named\s+)?(.+?)"
        r"(?=(?:\s*,?\s*(?:and\s+)?(?:with\s+)?rows?\b)|$)",
        text, flags=re.I,
    )
    if not columns_match:
        return None

    raw_columns = columns_match.group(1).strip(" ,.")
    columns = _split_items(raw_columns)
    if not 1 <= len(columns) <= 50:
        return None
    if len(columns) > 10:
        # Usually an NLP parsing failure; don't save garbage columns.
        return None

    rows_match = re.search(r"\brows?\s+(.+)$", text, flags=re.I)
    if not rows_match:
        return {"path": path, "columns": columns, "rows": []}

    raw_rows = rows_match.group(1).strip(" ,.")
    if not raw_rows:
        return {"path": path, "columns": columns, "rows": []}

    if len(columns) == 2:
        # Natural speech: "rows Rent 800, Internet 50".
        records = []
        for piece in re.split(r"\s*[,;]\s*", raw_rows):
            match = re.fullmatch(r"(.+?)\s+(-?\d+(?:\.\d+)?)", piece)
            if match:
                records.append([match.group(1).strip(" '\""), _numeric(match.group(2))])
            elif "|" in piece:
                cells = [x.strip() for x in piece.split("|")]
                if len(cells) != 2:
                    return None
                records.append([_numeric(cell) for cell in cells])
            else:
                return None
        return {"path": path, "columns": columns, "rows": records}

    # Unambiguous multi-column format: "rows A|B|C; D|E|F".
    if "|" in raw_rows:
        records = []
        for piece in re.split(r"\s*;\s*", raw_rows):
            cells = [_numeric(cell) for cell in piece.split("|")]
            if len(cells) != len(columns):
                return None
            records.append(cells)
        return {"path": path, "columns": columns, "rows": records}

    return None


def work_intent(text):
    """Return (matched, plan). A matched but incomplete intent gives guidance.

    Unknown requests return (False, None) so existing routes still work.
    """
    raw = _clean(text)
    lowered = raw.lower()

    # Most-common Gmail commands: no LLM planner round trip.
    if _has(lowered, r"\b(?:gmail|e-?mails?|mails?|inbox|mailbox)\b"):
        if _has(lowered, r"\b(?:summari[sz]e|summary|brief|briefing|recap|catch me up|check|review|catch up)\b"):
            return True, _task("gmail_summary_24h")
        if _has(lowered, r"\b(?:list|show|read|what(?:'s| is) new)\b") and _has(
            lowered, r"\b(?:last|past|recent|today|24|new)\b"
        ):
            return True, _task("gmail_list_24h")

    # Sending requires a pre-existing draft and a separate GUI confirmation.
    if re.fullmatch(
        r"(?:please\s+)?send\s+(?:(?:the|my|that|last|latest)\s+)?"
        r"(?:prepared\s+)?(?:email|e-mail|draft|message)(?:\s+now)?",
        lowered,
    ):
        return True, _task("gmail_send_draft", {"draft_id": "last"})

    # Drafting: require exact address; never invent sender/recipient/subject.
    if _has(
        lowered,
        r"^(?:can you\s+)?(?:write|draft|compose|prepare|generate|create)"
        r"\b.*\b(?:email|e-mail)\b",
    ):
        match = re.search(
            r"\bto\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b"
            r"\s+(?:about|regarding|with\s+subject)\s+(.+)$",
            raw, flags=re.I,
        )
        if not match:
            return True, _reply(
                "I can draft that. Please give me the recipient's full email "
                "address and subject, for example: Draft an email to "
                "alex@example.com about the project update."
            )
        recipient, subject = match.group(1), match.group(2).strip()
        return True, _task("gmail_prepare_email", {
            "to": recipient, "subject": subject[:150],
            "instructions": "Write an appropriate, clear email about: " + subject,
        })

    # Signed-in pages. All authentication is performed by the user manually.
    if _has(lowered, r"\b(?:log\s*in|sign\s*in)\b") and _has(
        lowered, r"\b(?:account|website|site|browser)\b"
    ):
        return True, _task("browser_account_login_help")
    if _has(lowered, r"\b(?:page|dashboard|website|webpage|account)\b") and _has(
        lowered, r"\b(?:summari[sz]e|summary|overview|describe|what(?:'s| is) on|read|review|inspect|look at|check)\b"
    ):
        return True, _task("browser_account_overview", {"question": raw})

    # Simple file creation. Complex requests intentionally go to the
    # specialised document planner rather than the enormous general planner.
    action = _has(lowered, r"^(?:(?:can|could|would) you\s+)?(?:create|make|generate|build|write|prepare|produce|draft)\b")
    if not action:
        return False, None

    work_type = None
    if _has(lowered, r"\b(?:excel|spreadsheet|workbook|xlsx|x l)\b|\.xlsx\b"):
        work_type = "xlsx"
    elif _has(lowered, r"\b(?:csv|comma separated)\b|\.csv\b"):
        work_type = "csv"
    elif _has(lowered, r"\b(?:word|docx|document|report|letter|proposal)\b|\.docx\b"):
        work_type = "docx"
    elif _has(lowered, r"\b(?:powerpoint|presentation|slides)\b|\.pptx\b"):
        work_type = "pptx"

    if not work_type:
        return False, None

    path = _filename(raw, work_type)
    if not path:
        return True, _reply(
            f"I can create a {work_type.upper()} file. Please give it a "
            f"filename ending in .{work_type}, for example "
            f"expenses.{work_type} in Documents."
        )

    if work_type in {"xlsx", "csv"}:
        arguments = _sheet_data(raw, path)
        if arguments is not None:
            return True, _task(
                "create_spreadsheet" if work_type == "xlsx" else "create_csv",
                arguments,
            )
    # Word/PowerPoint and ambiguous tables need a focused AI planner.
    return False, None


def is_work_document_request(text):
    text = _clean(text).lower()
    return bool(
        _has(text, r"^(?:(?:can|could|would) you\s+)?(?:create|make|generate|build|write|prepare|produce|draft)\b")
        and _has(
            text,
            r"\b(?:excel|spreadsheet|workbook|word|docx|document|report|letter|"
            r"proposal|powerpoint|presentation|slides|csv|xlsx)\b|\.(?:xlsx|docx|pptx|csv)\b",
        )
    )
