import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from send2trash import send2trash

from tools.paths import resolve_path
from tools.registry import register


TEXT_EXTS = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".csv",
    ".log",
    ".ini",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".xml",
    ".toml",
}

READABLE_EXTS = TEXT_EXTS | {
    ".pdf",
    ".docx",
}

MAX_SEARCH_RESULTS = 60
MAX_SCAN_ITEMS = 10000


# =========================================================
# INTERNAL HELPERS
# =========================================================

def _read(path, max_chars=30000):
    p = resolve_path(path)

    if not p.exists():
        raise FileNotFoundError(p)

    if not p.is_file():
        raise ValueError(f"Not a file: {p}")

    ext = p.suffix.lower()

    if ext in TEXT_EXTS:
        return p.read_text(
            encoding="utf-8",
            errors="replace",
        )[: int(max_chars)]

    if ext == ".pdf":
        from pypdf import PdfReader

        text = "\n".join(
            (page.extract_text() or "")
            for page in PdfReader(str(p)).pages
        )
        return text[: int(max_chars)]

    if ext == ".docx":
        from docx import Document

        text = "\n".join(
            paragraph.text
            for paragraph in Document(str(p)).paragraphs
        )
        return text[: int(max_chars)]

    raise ValueError(
        f"Unsupported document type: {ext or '[no extension]'}"
    )


def _safe_new_name(value):
    name = Path(str(value)).name.strip()

    if not name or name in {".", ".."}:
        raise ValueError("Invalid file or folder name.")

    return name


def _iter_paths(root):
    root_path = resolve_path(root)

    count = 0

    try:
        iterator = root_path.rglob("*")

        for item in iterator:
            count += 1

            if count > MAX_SCAN_ITEMS:
                break

            yield item

    except (PermissionError, OSError):
        return


def _copy_path_impl(source, destination):
    source_path = resolve_path(source)
    destination_path = resolve_path(destination)

    if not source_path.exists():
        raise FileNotFoundError(source_path)

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if source_path.is_dir():
        if destination_path.exists() and destination_path.is_dir():
            destination_path = destination_path / source_path.name

        shutil.copytree(
            source_path,
            destination_path,
            dirs_exist_ok=True,
        )
    else:
        if destination_path.exists() and destination_path.is_dir():
            destination_path = destination_path / source_path.name

        shutil.copy2(
            source_path,
            destination_path,
        )

    return destination_path


# =========================================================
# LIST / FIND / INFO
# =========================================================

@register(
    "list_files",
    "List files and folders. Supports home/desktop/documents/downloads/"
    "pictures/music/videos aliases. arguments={folder?,recursive?,limit?}",
)
def list_files(
    folder="home",
    recursive=False,
    limit=150,
):
    path = resolve_path(folder)

    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_dir():
        raise ValueError(f"Not a folder: {path}")

    limit = max(
        1,
        min(int(limit), 500),
    )

    if bool(recursive):
        items = []

        for item in _iter_paths(str(path)):
            items.append(item)

            if len(items) >= limit:
                break
    else:
        items = list(path.iterdir())[:limit]

    if not items:
        return "Folder is empty."

    lines = []

    for item in items:
        kind = "DIR" if item.is_dir() else "FILE"
        lines.append(f"[{kind}] {item}")

    return "\n".join(lines)


@register(
    "search_files",
    "Search filenames recursively and return matching full paths. "
    "arguments={query,root?,limit?}",
)
def search_files(
    query,
    root="home",
    limit=MAX_SEARCH_RESULTS,
):
    query_text = str(query).lower().strip()

    if not query_text:
        raise ValueError("Search query is empty.")

    limit = max(
        1,
        min(int(limit), 200),
    )

    results = []

    for item in _iter_paths(root):
        try:
            if query_text in item.name.lower():
                results.append(str(item))

            if len(results) >= limit:
                break

        except (PermissionError, OSError):
            continue

    return "\n".join(results) if results else "No matches."


@register(
    "find_file",
    "Find the best matching file or folder and return ONLY its full path. "
    "Useful before move/copy/rename/open operations. "
    "arguments={query,root?,kind?}",
)
def find_file(
    query,
    root="home",
    kind="any",
):
    query_text = str(query).lower().strip()

    if not query_text:
        raise ValueError("Search query is empty.")

    kind_text = str(kind).lower().strip()

    if kind_text not in {
        "any",
        "file",
        "folder",
        "dir",
        "directory",
    }:
        raise ValueError("kind must be any, file, or folder.")

    candidates = []

    for item in _iter_paths(root):
        try:
            if kind_text == "file" and not item.is_file():
                continue

            if kind_text in {"folder", "dir", "directory"} and not item.is_dir():
                continue

            name = item.name.lower()
            stem = item.stem.lower()

            if query_text not in name and query_text not in stem:
                continue

            score = 0

            if name == query_text:
                score += 1000

            if stem == query_text:
                score += 950

            if name.startswith(query_text):
                score += 400

            if stem.startswith(query_text):
                score += 350

            if query_text in name:
                score += 150

            # Prefer recently modified items when names are equally good.
            try:
                modified = item.stat().st_mtime
            except OSError:
                modified = 0

            candidates.append(
                (
                    score,
                    modified,
                    str(item),
                )
            )

        except (PermissionError, OSError):
            continue

    if not candidates:
        return ""

    candidates.sort(
        key=lambda row: (
            row[0],
            row[1],
        ),
        reverse=True,
    )

    return candidates[0][2]


@register(
    "file_info",
    "Get details about a local file or folder. arguments={path}",
)
def file_info(path):
    item = resolve_path(path)

    if not item.exists():
        raise FileNotFoundError(item)

    stat = item.stat()

    kind = "folder" if item.is_dir() else "file"

    lines = [
        f"Path: {item}",
        f"Type: {kind}",
        f"Size: {stat.st_size} bytes",
        f"Modified timestamp: {stat.st_mtime}",
    ]

    if item.is_file():
        lines.append(f"Extension: {item.suffix.lower() or '[none]'}")

    return "\n".join(lines)


# =========================================================
# OPEN
# =========================================================

@register(
    "open_path",
    "Open a local file or folder with Windows/default application. "
    "arguments={path}",
)
def open_path(path):
    item = resolve_path(path)

    if not item.exists():
        raise FileNotFoundError(item)

    if hasattr(os, "startfile"):
        os.startfile(str(item))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(item)])
    else:
        subprocess.Popen(["xdg-open", str(item)])

    return f"Opened {item}"


# =========================================================
# READ / SEARCH DOCUMENT CONTENT
# =========================================================

@register(
    "read_document",
    "Read local txt/md/code/csv/json/pdf/docx content. arguments={path}",
)
def read_document(path):
    return _read(path)


@register(
    "search_documents",
    "Search readable local documents by content and rank matches. "
    "arguments={query,root?}",
)
def search_documents(
    query,
    root="documents",
):
    terms = [
        term
        for term in str(query).lower().split()
        if len(term) > 2
    ]

    if not terms:
        raise ValueError("Search query is too short.")

    scores = []

    for item in _iter_paths(root):
        if not item.is_file() or item.suffix.lower() not in READABLE_EXTS:
            continue

        try:
            content = _read(
                str(item),
                max_chars=12000,
            ).lower()

            score = sum(
                content.count(term)
                for term in terms
            )

            if score:
                scores.append(
                    (
                        score,
                        item,
                    )
                )

        except Exception:
            continue

    scores.sort(
        key=lambda row: row[0],
        reverse=True,
    )

    if not scores:
        return "No relevant documents found."

    return "\n".join(
        f"{score}: {path}"
        for score, path in scores[:10]
    )


@register(
    "ask_documents",
    "Answer a question using local documents. arguments={question,root?}",
)
def ask_documents(
    question,
    root="documents",
):
    from ai.ollama import answer_with_context

    terms = [
        term
        for term in str(question).lower().split()
        if len(term) > 3
    ]

    candidates = []

    for item in _iter_paths(root):
        if not item.is_file() or item.suffix.lower() not in READABLE_EXTS:
            continue

        try:
            content = _read(
                str(item),
                max_chars=9000,
            )

            lowered = content.lower()

            score = sum(
                lowered.count(term)
                for term in terms
            )

            if score:
                candidates.append(
                    (
                        score,
                        item,
                        content,
                    )
                )

        except Exception:
            continue

    candidates.sort(
        key=lambda row: row[0],
        reverse=True,
    )

    context = "\n\n".join(
        f"FILE: {item}\n{text}"
        for _, item, text in candidates[:4]
    )

    if not context:
        return "I couldn't find relevant local documents."

    return answer_with_context(
        question,
        context,
    )


# =========================================================
# CREATE / EDIT
# =========================================================

@register(
    "create_folder",
    "Create a local folder. arguments={path}",
)
def create_folder(path):
    item = resolve_path(path)

    item.mkdir(
        parents=True,
        exist_ok=True,
    )

    return f"Created {item}"


@register(
    "write_text_file",
    "Create or replace a text/code file. "
    "arguments={path,content}",
)
def write_text_file(
    path,
    content,
):
    item = resolve_path(path)

    allowed = TEXT_EXTS

    if item.suffix.lower() not in allowed:
        raise ValueError(
            "Unsupported writable file type."
        )

    item.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    item.write_text(
        str(content),
        encoding="utf-8",
    )

    return f"Saved {item}"


@register(
    "append_text_file",
    "Append text to an existing or new text/code file. "
    "arguments={path,content,newline?}",
)
def append_text_file(
    path,
    content,
    newline=True,
):
    item = resolve_path(path)

    if item.suffix.lower() not in TEXT_EXTS:
        raise ValueError(
            "Unsupported writable file type."
        )

    item.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    text = str(content)

    if bool(newline) and item.exists() and item.stat().st_size > 0:
        text = "\n" + text

    with item.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(text)

    return f"Appended text to {item}"


@register(
    "replace_text_in_file",
    "Replace text inside a local text/code file. Confirmation required. "
    "arguments={path,old,new,replace_all?}",
)
def replace_text_in_file(
    path,
    old,
    new,
    replace_all=True,
):
    item = resolve_path(path)

    if not item.is_file():
        raise FileNotFoundError(item)

    if item.suffix.lower() not in TEXT_EXTS:
        raise ValueError(
            "Unsupported editable file type."
        )

    original = item.read_text(
        encoding="utf-8",
        errors="replace",
    )

    old_text = str(old)

    if not old_text:
        raise ValueError(
            "The text to replace cannot be empty."
        )

    if old_text not in original:
        return "The requested text was not found in the file."

    if bool(replace_all):
        updated = original.replace(
            old_text,
            str(new),
        )
    else:
        updated = original.replace(
            old_text,
            str(new),
            1,
        )

    item.write_text(
        updated,
        encoding="utf-8",
    )

    return f"Updated {item}"


# =========================================================
# COPY / MOVE / RENAME / DELETE
# =========================================================

@register(
    "copy_path",
    "Copy a file or folder. arguments={source,destination}",
)
def copy_path(
    source,
    destination,
):
    destination_path = _copy_path_impl(
        source,
        destination,
    )

    return f"Copied to {destination_path}"


@register(
    "copy_file",
    "Copy a file. Kept for compatibility. arguments={source,destination}",
)
def copy_file(
    source,
    destination,
):
    source_path = resolve_path(source)

    if not source_path.is_file():
        raise ValueError(
            "copy_file only accepts files. Use copy_path for folders."
        )

    destination_path = _copy_path_impl(
        source,
        destination,
    )

    return f"Copied to {destination_path}"


@register(
    "move_file",
    "Move a file or folder. Confirmation required. "
    "arguments={source,destination}",
)
def move_file(
    source,
    destination,
):
    source_path = resolve_path(source)
    destination_path = resolve_path(destination)

    if not source_path.exists():
        raise FileNotFoundError(source_path)

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = shutil.move(
        str(source_path),
        str(destination_path),
    )

    return f"Moved to {result}"


@register(
    "rename_file",
    "Rename a file or folder. Confirmation required. "
    "arguments={path,new_name}",
)
def rename_file(
    path,
    new_name,
):
    item = resolve_path(path)

    if not item.exists():
        raise FileNotFoundError(item)

    destination = item.with_name(
        _safe_new_name(new_name)
    )

    item.rename(
        destination
    )

    return f"Renamed to {destination}"


@register(
    "delete_path",
    "Move a file or folder to the Recycle Bin. Confirmation required. "
    "arguments={path}",
)
def delete_path(path):
    item = resolve_path(path)

    if not item.exists():
        raise FileNotFoundError(item)

    send2trash(
        str(item)
    )

    return f"Moved {item} to the Recycle Bin."


# =========================================================
# ZIP
# =========================================================

@register(
    "zip_path",
    "Create a ZIP archive from a file or folder. "
    "arguments={source,destination}",
)
def zip_path(
    source,
    destination,
):
    source_path = resolve_path(source)
    destination_path = resolve_path(destination)

    if not source_path.exists():
        raise FileNotFoundError(source_path)

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if destination_path.suffix.lower() != ".zip":
        destination_path = destination_path.with_suffix(
            ".zip"
        )

    with zipfile.ZipFile(
        destination_path,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        if source_path.is_file():
            archive.write(
                source_path,
                source_path.name,
            )
        else:
            for item in source_path.rglob("*"):
                if item.is_file():
                    archive.write(
                        item,
                        item.relative_to(
                            source_path.parent
                        ),
                    )

    return f"Created {destination_path}"


@register(
    "unzip_archive",
    "Extract a ZIP archive. arguments={archive,destination}",
)
def unzip_archive(
    archive,
    destination,
):
    archive_path = resolve_path(archive)
    destination_path = resolve_path(destination)

    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)

    destination_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    with zipfile.ZipFile(
        archive_path
    ) as archive_handle:
        for member in archive_handle.infolist():
            target = (
                destination_path
                / member.filename
            ).resolve()

            if (
                target != destination_path
                and destination_path not in target.parents
            ):
                raise ValueError(
                    "Unsafe archive path detected."
                )

        archive_handle.extractall(
            destination_path
        )

    return f"Extracted to {destination_path}"


# =========================================================
# SEMANTIC SEARCH
# =========================================================

@register(
    "semantic_search_documents",
    "Semantic search across local documents using the optional local "
    "Ollama embedding model. arguments={query,root?}",
)
def semantic_search_documents(
    query,
    root="documents",
):
    import math

    from ai.ollama import embed

    documents = []

    for item in _iter_paths(root):
        if not item.is_file() or item.suffix.lower() not in READABLE_EXTS:
            continue

        try:
            content = _read(
                str(item),
                max_chars=5000,
            ).strip()

            if content:
                documents.append(
                    (
                        item,
                        content,
                    )
                )

            if len(documents) >= 40:
                break

        except Exception:
            continue

    if not documents:
        return "No readable documents found."

    try:
        vectors = embed(
            [str(query)]
            + [
                content
                for _, content in documents
            ]
        )
    except Exception as exc:
        return (
            "Local embedding search is unavailable "
            f"({exc}). Use search_documents instead."
        )

    if len(vectors) != len(documents) + 1:
        return (
            "The local embedding model returned "
            "an unexpected result."
        )

    query_vector = vectors[0]

    def cosine(a, b):
        dot = sum(
            x * y
            for x, y in zip(a, b)
        )

        norm_a = math.sqrt(
            sum(x * x for x in a)
        ) or 1.0

        norm_b = math.sqrt(
            sum(x * x for x in b)
        ) or 1.0

        return dot / (
            norm_a * norm_b
        )

    ranked = sorted(
        (
            (
                cosine(
                    query_vector,
                    vector,
                ),
                item,
            )
            for (item, _), vector
            in zip(
                documents,
                vectors[1:],
            )
        ),
        reverse=True,
        key=lambda row: row[0],
    )

    return "\n".join(
        f"{score:.3f}: {item}"
        for score, item in ranked[:8]
    )
