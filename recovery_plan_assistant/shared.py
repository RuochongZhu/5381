from __future__ import annotations

import inspect
import json
import os
import re
import shutil
import subprocess
import textwrap
import time
import warnings
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont
from urllib3.exceptions import NotOpenSSLWarning

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "recovery_projects.csv"
OUTPUT_DIR = BASE_DIR / "output"
SCREENSHOT_DIR = BASE_DIR / "screenshots"

warnings.filterwarnings("ignore", category=NotOpenSSLWarning)

DEFAULT_MODEL = "qwen2.5:3b"
MODEL = DEFAULT_MODEL

OLLAMA_HOST = "http://127.0.0.1:11434"
CHAT_URL = f"{OLLAMA_HOST}/api/chat"
TAGS_URL = f"{OLLAMA_HOST}/api/tags"
REQUEST_TIMEOUT = 300
OLLAMA_BIN = Path("/Applications/Ollama.app/Contents/Resources/ollama")
WORD_RE = re.compile(r"[a-z0-9]+")

PRIORITY_ORDER = {"High": 3, "Medium": 2, "Low": 1}
TOOLS_BY_NAME: dict[str, Any] = {}


def configure_from_env() -> None:
    global MODEL, OLLAMA_HOST, CHAT_URL, TAGS_URL

    MODEL = os.environ.get("DSAI_MODEL", DEFAULT_MODEL).strip()
    MODEL = MODEL or DEFAULT_MODEL

    OLLAMA_HOST = os.environ.get("OLLAMA_HOST", OLLAMA_HOST).rstrip("/")
    CHAT_URL = f"{OLLAMA_HOST}/api/chat"
    TAGS_URL = f"{OLLAMA_HOST}/api/tags"


configure_from_env()


def ensure_directories() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def ollama_is_running() -> bool:
    try:
        response = requests.get(TAGS_URL, timeout=2)
        return response.ok
    except requests.RequestException:
        return False


def ensure_ollama_running(max_wait_seconds: int = 20) -> None:
    if ollama_is_running():
        return

    if OLLAMA_BIN.exists():
        subprocess.Popen(
            ["open", "-a", "Ollama"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        found = shutil.which("ollama")
        if found:
            subprocess.Popen(
                [found, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            raise RuntimeError(
                "Ollama is not installed. Install it first or set OLLAMA_HOST to a running server."
            )

    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        if ollama_is_running():
            return
        time.sleep(0.5)

    raise RuntimeError(f"Ollama did not start at {OLLAMA_HOST} within {max_wait_seconds} seconds.")


def ensure_model_available(model: str = MODEL) -> None:
    ensure_ollama_running()
    response = requests.get(TAGS_URL, timeout=10)
    response.raise_for_status()
    models = response.json().get("models", [])
    available = {item.get("model", "") for item in models}
    if not any(name == model or name.startswith(f"{model}:") for name in available):
        raise RuntimeError(
            f"Model '{model}' is not available locally. Run:\n"
            f"  {OLLAMA_BIN if OLLAMA_BIN.exists() else 'ollama'} pull {model}"
        )


def load_projects() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def tokenize(text: str) -> set[str]:
    return set(WORD_RE.findall(str(text).lower()))


def _search_blob(row: pd.Series) -> str:
    return " ".join(
        [
            str(row["community"]),
            str(row["project_title"]),
            str(row["sector"]),
            str(row["issue"]),
            str(row["action"]),
            str(row["priority"]),
        ]
    )


def search_recovery_projects(query: str, community: str = "", sector: str = "", top_n: int = 4) -> str:
    df = load_projects().copy()

    if community:
        df = df[df["community"].str.lower() == community.lower()]
    if sector:
        df = df[df["sector"].str.lower() == sector.lower()]

    if df.empty:
        return json.dumps([], indent=2)

    query_tokens = tokenize(query)

    def score_row(row: pd.Series) -> int:
        score = len(query_tokens & tokenize(_search_blob(row)))
        if community and row["community"].lower() == community.lower():
            score += 2
        if sector and row["sector"].lower() == sector.lower():
            score += 1
        score += PRIORITY_ORDER.get(str(row["priority"]), 0)
        return score

    df["score"] = df.apply(score_row, axis=1)
    df = df.sort_values(["score", "priority"], ascending=[False, False]).head(int(top_n))

    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "community": row["community"],
                "project_title": row["project_title"],
                "sector": row["sector"],
                "issue": row["issue"],
                "action": row["action"],
                "priority": row["priority"],
                "source_note": row["source_note"],
                "score": int(row["score"]),
            }
        )
    return json.dumps(records, indent=2)


def summarize_sector_counts(community: str = "") -> str:
    df = load_projects().copy()
    if community:
        df = df[df["community"].str.lower() == community.lower()]

    if df.empty:
        return json.dumps([], indent=2)

    summary = (
        df.groupby(["community", "sector"])
        .size()
        .reset_index(name="project_count")
        .sort_values(["community", "project_count", "sector"], ascending=[True, False, True])
    )
    return summary.to_json(orient="records", indent=2)


def _coerce_rating(value: Any) -> int:
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, (int, float)):
        num = int(round(value))
    else:
        match = re.search(r"-?\d+", str(value))
        if not match:
            raise ValueError(f"Could not parse rating from value: {value}")
        num = int(match.group(0))
    return max(1, min(5, num))


def calculate_priority_score(impact: int, feasibility: int, urgency: int) -> str:
    impact_value = _coerce_rating(impact)
    feasibility_value = _coerce_rating(feasibility)
    urgency_value = _coerce_rating(urgency)

    score = round((impact_value * 0.45) + (feasibility_value * 0.20) + (urgency_value * 0.35), 2)
    if score >= 4.4:
        label = "Immediate priority"
    elif score >= 3.6:
        label = "Strong candidate"
    elif score >= 2.8:
        label = "Secondary candidate"
    else:
        label = "Low priority"

    return json.dumps(
        {
            "impact": impact_value,
            "feasibility": feasibility_value,
            "urgency": urgency_value,
            "weighted_score": score,
            "label": label,
        },
        indent=2,
    )


tool_search_recovery_projects = {
    "type": "function",
    "function": {
        "name": "search_recovery_projects",
        "description": "Search the local recovery project dataset for projects relevant to a community problem or planning question.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords describing the problem, need, or project type to search for.",
                },
                "community": {
                    "type": "string",
                    "description": "Optional exact community filter such as Red Hook or Long Beach.",
                },
                "sector": {
                    "type": "string",
                    "description": "Optional exact sector filter such as Transportation or Public Health.",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Maximum number of matching projects to return.",
                    "default": 4,
                },
            },
            "required": ["query"],
        },
    },
}

tool_summarize_sector_counts = {
    "type": "function",
    "function": {
        "name": "summarize_sector_counts",
        "description": "Summarize how many recovery projects exist in each sector, optionally for one community.",
        "parameters": {
            "type": "object",
            "properties": {
                "community": {
                    "type": "string",
                    "description": "Optional exact community filter such as Red Hook or Long Beach.",
                }
            },
            "required": [],
        },
    },
}

tool_calculate_priority_score = {
    "type": "function",
    "function": {
        "name": "calculate_priority_score",
        "description": "Calculate a weighted priority score from impact, feasibility, and urgency values on a 1-5 scale.",
        "parameters": {
            "type": "object",
            "properties": {
                "impact": {
                    "type": "integer",
                    "description": "Expected community impact on a 1-5 scale.",
                },
                "feasibility": {
                    "type": "integer",
                    "description": "Implementation feasibility on a 1-5 scale.",
                },
                "urgency": {
                    "type": "integer",
                    "description": "Urgency on a 1-5 scale.",
                },
            },
            "required": ["impact", "feasibility", "urgency"],
        },
    },
}

TOOLS_BY_NAME.update(
    {
        "search_recovery_projects": search_recovery_projects,
        "summarize_sector_counts": summarize_sector_counts,
        "calculate_priority_score": calculate_priority_score,
    }
)


def run_chat(messages: list[dict[str, Any]], model: str = MODEL, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    ensure_model_available(model)
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 700},
    }
    if tools is not None:
        body["tools"] = tools

    response = requests.post(CHAT_URL, json=body, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _normalize_arguments(raw_args: Any) -> dict[str, Any]:
    if isinstance(raw_args, str):
        return json.loads(raw_args)
    return dict(raw_args or {})


def _tool_output_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2)


def run_agent(
    role: str,
    task: str,
    model: str = MODEL,
    tools: list[dict[str, Any]] | None = None,
    max_tool_rounds: int = 4,
    return_details: bool = False,
) -> Any:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": role},
        {"role": "user", "content": task},
    ]
    tool_events: list[dict[str, Any]] = []

    for _ in range(max_tool_rounds + 1):
        result = run_chat(messages=messages, model=model, tools=tools)
        message = result.get("message", {})
        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            final_text = message.get("content", "").strip()
            payload = {"final_text": final_text, "tool_events": tool_events, "messages": messages + [message]}
            return payload if return_details else final_text

        messages.append(message)

        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            func_args = _normalize_arguments(tool_call["function"].get("arguments", {}))
            func = TOOLS_BY_NAME[func_name]
            try:
                output = _tool_output_text(func(**func_args))
            except Exception as exc:
                output = json.dumps(
                    {
                        "error": str(exc),
                        "tool_name": func_name,
                        "arguments": func_args,
                    },
                    indent=2,
                )
            event = {"name": func_name, "arguments": func_args, "output": output}
            tool_events.append(event)
            messages.append(
                {
                    "role": "tool",
                    "name": func_name,
                    "content": output,
                }
            )

    fallback = {"final_text": tool_events[-1]["output"] if tool_events else "", "tool_events": tool_events, "messages": messages}
    return fallback if return_details else fallback["final_text"]


def source_of(obj: Any) -> str:
    return inspect.getsource(obj).strip()


def write_output(stem: str, text: str) -> Path:
    ensure_directories()
    path = OUTPUT_DIR / f"{stem}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def render_terminal_screenshot(title: str, body_text: str, output_path: Path) -> Path:
    ensure_directories()

    title_font = _load_font(20)
    body_font = _load_font(16)

    wrapped_lines: list[str] = []
    for line in body_text.splitlines() or [""]:
        wrapped = textwrap.wrap(line, width=100, replace_whitespace=False, drop_whitespace=False)
        wrapped_lines.extend(wrapped or [""])

    line_height = 24
    width = 1280
    height = max(720, 110 + (len(wrapped_lines) + 2) * line_height)
    image = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((24, 24, width - 24, height - 24), radius=18, fill="#111827", outline="#334155", width=2)
    draw.rectangle((24, 24, width - 24, 72), fill="#1f2937")
    draw.ellipse((44, 40, 58, 54), fill="#ef4444")
    draw.ellipse((66, 40, 80, 54), fill="#f59e0b")
    draw.ellipse((88, 40, 102, 54), fill="#10b981")
    draw.text((128, 36), title, font=title_font, fill="#e5e7eb")

    y = 96
    for line in wrapped_lines:
        draw.text((44, y), line, font=body_font, fill="#d1d5db")
        y += line_height

    image.save(output_path)
    return output_path
