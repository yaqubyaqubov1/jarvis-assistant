"""Single-purpose document planner for local Qwen.

Validate the model output and take the filepath from the user's request,
never from model-generated data.
"""
import json
import re

from ai.ollama import generate
from core.work_intents import _filename, _has, _reply, _task


def _kind_and_path(command):
    lowered = str(command).lower()
    for extension, pattern in (
        ("xlsx", r"\b(?:excel|spreadsheet|workbook)\b|\.xlsx\b"),
        ("csv", r"\bcsv\b|\.csv\b"),
        ("docx", r"\b(?:word document|word file|docx|report|letter|proposal)\b|\.docx\b"),
        ("pptx", r"\b(?:powerpoint|presentation|slides)\b|\.pptx\b"),
    ):
        if _has(lowered, pattern):
            return extension, _filename(command, extension)
    return None, None


def _extract_object(answer):
    answer = str(answer).strip()
    fence = chr(96) * 3
    if answer.startswith(fence):
        answer = re.sub(r"^.*?\n", "", answer, count=1)
        answer = answer.rsplit(fence, 1)[0]
    start, end = answer.find("{"), answer.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object returned by document planner.")
    return json.loads(answer[start:end + 1])


def _str(value, limit):
    return str(value or "")[:limit].strip()


def plan_document(command):
    kind, path = _kind_and_path(command)
    if kind is None:
        return None
    if not path:
        return _reply(
            f"Please include a name ending in .{kind}, such as "
            f"'create a {kind} file called project.{kind} in Documents'."
        )

    if kind in ("xlsx", "csv"):
        schema = '{"columns":["Column A","Column B"],"rows":[["Name",10],["Other",20]]}'
        instructions = (
            "Return column names and a list of rows. Each row must have "
            "exactly the same number of values as columns. Only include "
            "real data specified in the user's request. If no rows are "
            "supplied, use []. If columns were not supplied, choose "
            "clear generic headers without inventing factual observations. "
            "Rows must be arrays, NOT objects."
        )
    elif kind == "docx":
        schema = (
            '{"title":"Project summary","content":"Introductory text",'
            '"sections":[{"heading":"Goals","body":"Relevant content"}]}'
        )
        instructions = (
            "Write concise document content. If the request lacks "
            "facts, create a general-purpose template without inventing "
            "names, numbers or dates. Sections is optional."
        )
    else:
        schema = (
            '{"title":"Project update","slides":['
            '{"title":"Overview","bullets":["Point one","Point two"]},'
            '{"title":"Next steps","bullets":["Task one","Task two"]}]}'
        )
        instructions = (
            "Generate a short PowerPoint deck. Slide titles and bullets "
            "must match the requested purpose. Do not invent factual "
            "results, numbers, names or dates. Use 1-8 content slides."
        )

    prompt = (
        "Create a single structured work document for the user's Windows "
        "computer. Output ONLY valid JSON with double-quoted keys. "
        "No markdown, introduction or commentary.\n"
        f"FORMAT: {kind}\nSCHEMA EXAMPLE: {schema}\n"
        f"RULES: {instructions}\n"
        f"USER REQUEST: {str(command)[:2500]}\nJSON:"
    )

    try:
        response = _extract_object(
            generate(prompt, temperature=0.1, num_predict=1400)
        )
        if not isinstance(response, dict):
            raise ValueError("Expected object.")
        if kind in ("xlsx", "csv"):
            columns = response.get("columns")
            rows = response.get("rows", [])
            if (
                not isinstance(columns, list)
                or not 1 <= len(columns) <= 50
                or not all(isinstance(c, str) and c.strip() for c in columns)
                or not isinstance(rows, list)
                or len(rows) > 200
                or any(
                    not isinstance(row, list) or len(row) != len(columns)
                    for row in rows
                )
            ):
                raise ValueError("Invalid table columns or rows.")
            return _task(
                "create_spreadsheet" if kind == "xlsx" else "create_csv",
                {"path": path, "columns": columns, "rows": rows},
            )
        if kind == "docx":
            title = _str(response.get("title"), 200)
            content = _str(response.get("content"), 15000)
            sections = response.get("sections", [])
            if (
                not title
                or not isinstance(sections, list)
                or len(sections) > 20
                or any(
                    not isinstance(s, dict)
                    or not isinstance(s.get("heading"), str)
                    or not isinstance(s.get("body"), str)
                    for s in sections
                )
            ):
                raise ValueError("Invalid Word document structure.")
            sections = [
                {"heading": _str(s["heading"], 150),
                 "body": _str(s["body"], 6000)}
                for s in sections
            ]
            return _task(
                "create_word_document",
                {"path": path, "title": title,
                 "content": content, "sections": sections},
            )
        title = _str(response.get("title"), 200)
        slides = response.get("slides")
        if (
            not title or not isinstance(slides, list)
            or not 1 <= len(slides) <= 15
            or any(
                not isinstance(item, dict)
                or not isinstance(item.get("title"), str)
                or not isinstance(item.get("bullets"), list)
                or len(item["bullets"]) > 12
                or not all(isinstance(b, str) for b in item["bullets"])
                for item in slides
            )
        ):
            raise ValueError("Invalid presentation structure.")
        cleaned = [
            {"title": _str(item["title"], 160),
             "bullets": [_str(b, 300) for b in item["bullets"]]}
            for item in slides
        ]
        return _task(
            "create_presentation",
            {"path": path, "title": title, "slides": cleaned},
        )
    except (ValueError, json.JSONDecodeError, TypeError, KeyError):
        return _reply(
            "I understand this is a work-document request, but could not "
            "structure it reliably. Please try a shorter request that "
            f"includes a .{kind} filename and the content you want."
        )
