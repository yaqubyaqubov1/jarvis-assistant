import base64
import json
from pathlib import Path

import requests

from ai.prompts import JARVIS_PERSONALITY
from config import (
    OLLAMA_URL,
    OLLAMA_MODEL,
    VISION_MODEL,
    EMBEDDING_MODEL,
)
from core.cancellation import (
    TaskCancelled,
    checkpoint,
    cancel_requested,
    set_active_response,
    clear_active_response,
)


class OllamaError(RuntimeError):
    pass


def _stream_generate(payload, timeout=120):
    """Stream a local Ollama generation so it can be interrupted."""
    checkpoint()
    response = None

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            stream=True,
            timeout=(3, timeout),
        )

        set_active_response(response)
        response.raise_for_status()

        pieces = []

        for raw_line in response.iter_lines(decode_unicode=True):
            checkpoint()

            if not raw_line:
                continue

            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            if data.get("error"):
                raise OllamaError(str(data["error"]))

            piece = data.get("response", "")
            if piece:
                pieces.append(piece)

            if data.get("done"):
                break

        checkpoint()
        return "".join(pieces).strip()

    except TaskCancelled:
        raise

    except requests.RequestException as exc:
        if cancel_requested():
            raise TaskCancelled("Task cancelled.") from exc

        raise OllamaError(
            "Local Ollama is not reachable. Start Ollama and make sure "
            "the configured local model is installed."
        ) from exc

    finally:
        clear_active_response(response)

        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def _post_json(path, payload, timeout=120):
    checkpoint()

    try:
        response = requests.post(
            f"{OLLAMA_URL}{path}",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        checkpoint()
        return response.json()

    except TaskCancelled:
        raise

    except requests.RequestException as exc:
        if cancel_requested():
            raise TaskCancelled("Task cancelled.") from exc

        raise OllamaError(
            "Local Ollama is not reachable. Start Ollama and make sure "
            "the configured local model is installed."
        ) from exc


def generate(prompt, temperature=0.1, num_predict=512):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": str(prompt),
        "stream": True,
        "keep_alive": "30m",
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }

    return _stream_generate(payload)


def chat(message, history=None, context=""):
    history = history or []

    history_text = "\n".join(
        f"{item.get('role', 'user').upper()}: {item.get('content', '')}"
        for item in history[-8:]
    )

    prompt = f"""
{JARVIS_PERSONALITY}

Relevant context:
{context}

Conversation:
{history_text}

USER:
{message}

J.A.R.V.I.S.:
""".strip()

    return generate(
        prompt,
        temperature=0.35,
        num_predict=300,
    )


def answer_with_context(question, context):
    prompt = f"""
{JARVIS_PERSONALITY}

Answer the user's question using the supplied context.
If the context is insufficient, say so plainly.
Do not invent facts that are not present in the context.

QUESTION:
{question}

CONTEXT:
{str(context)[:24000]}

J.A.R.V.I.S.:
""".strip()

    return generate(
        prompt,
        temperature=0.15,
        num_predict=500,
    )


def describe_image(
    image_path,
    question=(
        "Describe what is visible on this screen and identify anything "
        "relevant to the user's request."
    ),
):
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(path)

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")

    payload = {
        "model": VISION_MODEL,
        "prompt": f"{JARVIS_PERSONALITY}\n\n{question}",
        "images": [encoded],
        "stream": True,
        "keep_alive": "15m",
        "options": {
            "temperature": 0.1,
            "num_predict": 500,
        },
    }

    return _stream_generate(payload, timeout=180)


def embed(texts):
    """Create embeddings using the local Ollama embedding model."""
    if isinstance(texts, str):
        texts = [texts]

    data = _post_json(
        "/api/embed",
        {
            "model": EMBEDDING_MODEL,
            "input": list(texts),
            "keep_alive": "15m",
        },
        timeout=180,
    )

    return data.get("embeddings", [])
