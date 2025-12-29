import argparse
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional

import urllib.error
import urllib.request

URL = "https://openrouter.ai/api/v1/endpoints/zdr"
OUTPUT_FILE = "openrouter-zdr.json"


def extract_endpoints(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, dict):
        possible = data.get("data") or data.get("endpoints")
        if isinstance(possible, list):
            return possible
        if isinstance(possible, dict):
            return [possible]
    if isinstance(data, list):
        return data
    return []


def pricing_note(pricing: Any) -> str:
    if not isinstance(pricing, dict):
        return "pricing: N/A"
    prompt = pricing.get("prompt")
    completion = pricing.get("completion")
    other = {k: v for k, v in pricing.items() if k not in {"prompt", "completion"}}
    parts = []
    if prompt is not None:
        parts.append(f"prompt={prompt}")
    if completion is not None:
        parts.append(f"completion={completion}")
    for key, value in other.items():
        parts.append(f"{key}={value}")
    if not parts:
        return "pricing: N/A"
    return f"pricing: {', '.join(parts)}"


def claude_variant(model_name: str) -> Optional[str]:
    lowered = model_name.lower()
    if "haiku" in lowered:
        return "Haiku"
    if "sonnet" in lowered:
        return "Sonnet"
    if "opus" in lowered:
        return "Opus"
    return None


def format_table(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "No ZDR endpoints found."
    headers = ["model_name", "provider_name", "context_length", "notes"]
    columns = {header: [header] for header in headers}
    for row in rows:
        for header in headers:
            columns[header].append(row.get(header, ""))
    widths = {header: max(len(value) for value in values) for header, values in columns.items()}

    def row_line(values: Iterable[str]) -> str:
        return "| " + " | ".join(
            value.ljust(widths[header]) for value, header in zip(values, headers)
        ) + " |"

    lines = [row_line(headers)]
    lines.append("| " + " | ".join("-" * widths[header] for header in headers) + " |")
    for row in rows:
        lines.append(
            row_line([row.get(header, "") for header in headers])
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch OpenRouter ZDR endpoints")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug information about the response payload",
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Missing OPENROUTER_API_KEY environment variable.", file=sys.stderr)
        return 2

    request = urllib.request.Request(
        URL,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status_code = response.status
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {error_body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"HTTP request failed: {exc}", file=sys.stderr)
        return 1

    if status_code >= 400:
        print(f"HTTP {status_code}: {body}", file=sys.stderr)
        return 1

    try:
        data = json.loads(body)
    except ValueError as exc:
        print(f"Failed to decode JSON: {exc}", file=sys.stderr)
        return 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)

    endpoints = extract_endpoints(data)

    if args.debug:
        data_type = type(data).__name__
        if isinstance(data, dict):
            keys = sorted(data.keys())
            print(f"Debug: top-level type={data_type} keys={keys}")
        else:
            print(f"Debug: top-level type={data_type}")
        print(f"Debug: extracted endpoints count={len(endpoints)}")
        if endpoints:
            sample = endpoints[:3]
            print("Debug: first endpoints sample:")
            print(json.dumps(sample, indent=2, sort_keys=True))

    extracted = []
    for entry in endpoints:
        model_name = entry.get("model_name") or entry.get("model") or ""
        provider_name = entry.get("provider_name") or entry.get("provider") or ""
        context_length = entry.get("context_length") or entry.get("context") or ""
        pricing = entry.get("pricing")
        extracted.append(
            {
                "model_name": str(model_name),
                "provider_name": str(provider_name),
                "context_length": str(context_length),
                "pricing": pricing,
            }
        )

    def rows_for(filter_fn, add_notes_fn=None) -> List[Dict[str, str]]:
        rows = []
        for entry in extracted:
            model = entry["model_name"]
            if not filter_fn(model):
                continue
            notes = pricing_note(entry.get("pricing"))
            if add_notes_fn:
                extra = add_notes_fn(model)
                if extra:
                    notes = f"{extra}; {notes}"
            rows.append(
                {
                    "model_name": entry["model_name"],
                    "provider_name": entry["provider_name"],
                    "context_length": entry["context_length"],
                    "notes": notes,
                }
            )
        return rows

    sections = {
        "DeepSeek models": rows_for(lambda m: m.startswith("deepseek/")),
        "GLM 4.7": rows_for(lambda m: m == "z-ai/glm-4.7"),
        "Claude models": rows_for(
            lambda m: m.startswith("anthropic/claude-"),
            lambda m: f"variant={claude_variant(m)}" if claude_variant(m) else None,
        ),
        "GPT-5.x models": rows_for(lambda m: m.startswith("openai/gpt-5")),
    }

    print("OpenRouter ZDR endpoints summary")
    print("=")
    for title, rows in sections.items():
        exists = "yes" if rows else "no"
        print(f"\n## {title} (exists: {exists})")
        print(format_table(rows))

    print("\nConclusion")
    print("-")
    usable = [title for title, rows in sections.items() if rows]
    absent = [title for title, rows in sections.items() if not rows]
    print(f"Usable with provider.zdr=true today: {', '.join(usable) if usable else 'none'}")
    print(f"Absent from ZDR list: {', '.join(absent) if absent else 'none'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
