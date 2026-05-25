#!/usr/bin/env python3
"""
magnifica-humanitas-eval: run_eval.py

Runs the three-turn encyclical conversation across five providers (Anthropic,
OpenAI, Google, xAI, Mistral) at two temperatures (0 and 1.0). Logs full
transcripts to transcripts/{model}_{temp}.json.

Usage:
    python run_eval.py                        # all models, both temps
    python run_eval.py --model anthropic      # one model only
    python run_eval.py --temp low             # one temperature only
    python run_eval.py --dry-run              # print prompts, no API calls
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent

def load_dotenv():
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            if val and not os.environ.get(key.strip()):
                os.environ[key.strip()] = val.strip()

load_dotenv()
PROMPTS = ROOT / "prompts"
TRANSCRIPTS = ROOT / "transcripts"

# ---------------------------------------------------------------------------
# Provider config
# ---------------------------------------------------------------------------

PROVIDERS = {
    "anthropic": {
        "model_id": "claude-opus-4-5",
        "display_name": "Claude",
        "builder_company": "Anthropic",
    },
    "openai": {
        "model_id": "gpt-4.1",
        "display_name": "GPT",
        "builder_company": "OpenAI",
    },
    "google": {
        "model_id": "gemini-2.5-pro",
        "display_name": "Gemini",
        "builder_company": "Google",
    },
    "xai": {
        "model_id": "grok-3",
        "display_name": "Grok",
        "builder_company": "xAI",
    },
    "mistral": {
        "model_id": "mistral-large-latest",
        "display_name": "Mistral",
        "builder_company": "Mistral AI",
    },
}

KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}

TEMPS = {
    "low": 0.0,
    "high": 1.0,
}

# ---------------------------------------------------------------------------
# Provider call functions
# ---------------------------------------------------------------------------

def call_anthropic(messages, system, model, temperature):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    kwargs = {
        "model": model,
        "max_tokens": 4096,
        "messages": messages,
        "temperature": temperature,
    }
    if system:
        kwargs["system"] = system
    msg = client.messages.create(**kwargs)
    return msg.content[0].text


def _openai_compatible(messages, system, model, api_key, temperature, base_url=None):
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    full = []
    if system:
        full.append({"role": "system", "content": system})
    full.extend(messages)
    resp = client.chat.completions.create(
        model=model,
        messages=full,
        temperature=temperature,
        max_completion_tokens=4096,
    )
    return resp.choices[0].message.content


def call_openai(messages, system, model, temperature):
    return _openai_compatible(messages, system, model, os.environ["OPENAI_API_KEY"], temperature)


def call_xai(messages, system, model, temperature):
    return _openai_compatible(
        messages, system, model, os.environ["XAI_API_KEY"], temperature,
        base_url="https://api.x.ai/v1",
    )


def call_mistral(messages, system, model, temperature):
    return _openai_compatible(
        messages, system, model, os.environ["MISTRAL_API_KEY"], temperature,
        base_url="https://api.mistral.ai/v1",
    )


def call_google(messages, system, model, temperature):
    import urllib.request
    api_key = os.environ["GOOGLE_API_KEY"]
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={api_key}"
    )
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    body = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": 4096,
            "temperature": temperature,
        },
    }
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}
    payload = json.dumps(body).encode()

    delays = [5, 15, 30, 60, 90]
    last_err = None
    for i, delay in enumerate([0] + delays):
        if delay:
            time.sleep(delay)
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.request.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504) and i < len(delays):
                continue
            raise
    raise last_err


CALLERS = {
    "anthropic": call_anthropic,
    "openai": call_openai,
    "google": call_google,
    "xai": call_xai,
    "mistral": call_mistral,
}


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def build_system_prompt(provider_key: str) -> str:
    template = (PROMPTS / "system.md").read_text()
    p = PROVIDERS[provider_key]
    return template.format(
        model_display_name=p["display_name"],
        builder_company=p["builder_company"],
    ).strip()


def load_turns() -> list[dict]:
    turns_data = json.loads((PROMPTS / "turns.json").read_text())
    return turns_data["turns"]


def compute_prompt_sha(system: str, turns: list[dict]) -> str:
    payload = system + "\n" + json.dumps([t["user_message"] for t in turns])
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run_one(provider_key: str, temp_label: str, dry_run: bool) -> dict:
    p = PROVIDERS[provider_key]
    temperature = TEMPS[temp_label]
    system = build_system_prompt(provider_key)
    turns = load_turns()
    p_sha = compute_prompt_sha(system, turns)

    record = {
        "provider": provider_key,
        "model_id": p["model_id"],
        "display_name": p["display_name"],
        "builder_company": p["builder_company"],
        "temperature": temperature,
        "temp_label": temp_label,
        "system_prompt": system,
        "prompt_sha": p_sha,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "transcript": [],
    }

    if dry_run:
        for turn in turns:
            record["transcript"].append({
                "turn": turn["id"],
                "label": turn["label"],
                "user": turn["user_message"],
                "assistant": "(dry-run, not called)",
            })
        return record

    caller = CALLERS[provider_key]
    messages = []
    try:
        for turn in turns:
            messages.append({"role": "user", "content": turn["user_message"]})
            t0 = time.time()
            assistant = caller(messages, system, p["model_id"], temperature)
            elapsed = round(time.time() - t0, 2)
            assistant_safe = assistant if assistant is not None else ""
            messages.append({"role": "assistant", "content": assistant_safe})
            entry = {
                "turn": turn["id"],
                "label": turn["label"],
                "user": turn["user_message"],
                "assistant": assistant,
                "latency_s": elapsed,
            }
            if assistant is None:
                entry["empty_response"] = True
                print(f"    turn {turn['id']} ({turn['label']}): {elapsed}s — EMPTY response")
            else:
                print(f"    turn {turn['id']} ({turn['label']}): {elapsed}s, {len(assistant)} chars")
            record["transcript"].append(entry)
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
        print(f"    ERROR: {record['error']}", file=sys.stderr)

    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    return record


def write_transcript_md(record: dict, path: Path):
    """Write a human-readable markdown transcript alongside the JSON."""
    lines = [
        f"# {record['display_name']} ({record['model_id']})",
        f"",
        f"**Provider:** {record['provider']}",
        f"**Temperature:** {record['temperature']} ({record['temp_label']})",
        f"**System prompt:** {record['system_prompt']}",
        f"**Run started:** {record.get('started_at', 'N/A')}",
        f"",
        f"---",
        f"",
    ]
    for entry in record["transcript"]:
        lines.append(f"## Turn {entry['turn']} — {entry['label']}")
        lines.append(f"")
        lines.append(f"### Prompt")
        lines.append(f"")
        lines.append(entry["user"])
        lines.append(f"")
        lines.append(f"### Response")
        lines.append(f"")
        lines.append(entry.get("assistant") or "*(no response)*")
        if entry.get("latency_s"):
            lines.append(f"")
            lines.append(f"*({entry['latency_s']}s)*")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
    if record.get("error"):
        lines.append(f"## Error")
        lines.append(f"")
        lines.append(f"```")
        lines.append(record["error"])
        lines.append(f"```")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run the Magnifica Humanitas eval")
    parser.add_argument("--model", choices=list(PROVIDERS.keys()),
                        help="Run a single model (default: all)")
    parser.add_argument("--temp", choices=["low", "high", "both"], default="both",
                        help="Temperature condition (default: both)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts without calling APIs")
    args = parser.parse_args()

    providers = [args.model] if args.model else list(PROVIDERS.keys())
    temps = ["low", "high"] if args.temp == "both" else [args.temp]

    if not args.dry_run:
        missing = [KEY_ENV[p] for p in providers if not os.environ.get(KEY_ENV[p])]
        if missing:
            sys.exit(f"Missing API keys: {', '.join(missing)}\n"
                     f"Set them with: export KEY_NAME=...")

    TRANSCRIPTS.mkdir(exist_ok=True)

    print(f"\nMagnifica Humanitas Eval")
    print(f"Models: {', '.join(providers)}")
    print(f"Temperatures: {', '.join(temps)}")
    print(f"{'(DRY RUN)' if args.dry_run else ''}\n")

    for temp_label in temps:
        print(f"\n{'='*60}")
        print(f"  TEMPERATURE: {temp_label} ({TEMPS[temp_label]})")
        print(f"{'='*60}")
        for provider_key in providers:
            p = PROVIDERS[provider_key]
            print(f"\n  [{provider_key}] {p['model_id']} @ temp {TEMPS[temp_label]}")
            record = run_one(provider_key, temp_label, args.dry_run)

            if not args.dry_run:
                json_path = TRANSCRIPTS / f"{provider_key}_{temp_label}.json"
                json_path.write_text(
                    json.dumps(record, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                md_path = TRANSCRIPTS / f"{provider_key}_{temp_label}.md"
                write_transcript_md(record, md_path)
                print(f"    -> {json_path.name}, {md_path.name}")

    print(f"\nDone.\n")


if __name__ == "__main__":
    main()
