"""Measure the same synthetic workload at the VM's selected Ollama endpoint."""

import argparse
import http.client
import json
import statistics
import sys
import time
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Final
from zoneinfo import ZoneInfo

MODEL: Final = "agent-lab-qwen:4b"
NANOSECONDS: Final = 1_000_000_000
PROMPT: Final = (
    "Explain how to make a scientific computation reproducible. Write six detailed paragraphs covering "
    "input data, pinned software versions, random seeds, experiment logs, validation and limitations. "
    "Use English prose and keep explaining until all six topics are covered."
)
type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None


@dataclass(frozen=True, slots=True, kw_only=True)
class Sample:
    phase: str
    wall_seconds: float
    total_seconds: float
    load_seconds: float
    prompt_tokens: int
    prompt_seconds: float
    generated_tokens: int
    generation_seconds: float
    tokens_per_second: float
    done_reason: str
    response: str


def integer_field(record: dict[str, JsonValue], name: str) -> int:
    value = record[name]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"Invalid Ollama metric: {name}.")
    return value


def post(payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
    connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=180)
    try:
        connection.request(
            "POST", "/api/generate", body=json.dumps(payload), headers={"Content-Type": "application/json"}
        )
        response = connection.getresponse()
        if response.status != HTTPStatus.OK:
            raise ValueError(f"Ollama returned HTTP {response.status}.")
        document: JsonValue = json.loads(response.read())
    finally:
        connection.close()
    if not isinstance(document, dict) or "error" in document:
        raise ValueError("Ollama returned an invalid generation response.")
    return document


def inspect_endpoint(path: str) -> dict[str, JsonValue]:
    connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=10)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        if response.status != HTTPStatus.OK:
            raise ValueError(f"Ollama metadata returned HTTP {response.status}.")
        document: JsonValue = json.loads(response.read())
    finally:
        connection.close()
    if not isinstance(document, dict):
        raise TypeError("Invalid Ollama metadata.")
    return document


def measure(phase: str, index: int) -> Sample:
    started = time.monotonic()
    result = post(
        {
            "model": MODEL,
            "prompt": f"Independent trial {index}. {PROMPT}",
            "stream": False,
            "think": False,
            "keep_alive": "5m",
            "options": {"num_ctx": 65536, "num_predict": 128, "temperature": 0, "seed": 42},
        },
    )
    elapsed = time.monotonic() - started
    output = result["response"]
    reason = result["done_reason"]
    if result["done"] is not True or not isinstance(output, str) or not output.strip() or not isinstance(reason, str):
        raise ValueError("Ollama did not complete a non-empty response.")
    count = integer_field(result, "eval_count")
    duration = integer_field(result, "eval_duration") / NANOSECONDS
    if count == 0 or duration == 0:
        raise ValueError("Ollama returned no generated tokens.")
    return Sample(
        phase=phase,
        wall_seconds=elapsed,
        total_seconds=integer_field(result, "total_duration") / NANOSECONDS,
        load_seconds=integer_field(result, "load_duration") / NANOSECONDS,
        prompt_tokens=integer_field(result, "prompt_eval_count"),
        prompt_seconds=integer_field(result, "prompt_eval_duration") / NANOSECONDS,
        generated_tokens=count,
        generation_seconds=duration,
        tokens_per_second=count / duration,
        done_reason=reason,
        response=output,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True, choices=("mac", "docker"))
    arguments = parser.parse_args()
    samples: list[Sample] = []
    version = inspect_endpoint("/api/version")
    models = inspect_endpoint("/api/tags")
    try:
        post({"model": MODEL, "keep_alive": 0})
        for index in range(4):
            sample = measure("after_unload" if index == 0 else "warm", index)
            samples.append(sample)
            sys.stderr.write(
                f"{arguments.backend} {sample.phase} {index}: {sample.wall_seconds:.2f}s, "
                f"{sample.tokens_per_second:.2f} tokens/s\n"
            )
            sys.stderr.flush()
        loaded_models = inspect_endpoint("/api/ps")
        warm = samples[1:]
        document = {
            "checked_at_utc": datetime.now(UTC).isoformat(),
            "checked_at_local": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
            "backend": arguments.backend,
            "version": version,
            "available_models": models,
            "loaded_models_after_requests": loaded_models,
            "model": MODEL,
            "client": "Linux VM loopback; Mac backend includes the reverse SSH tunnel",
            "protocol": {
                "prompt": PROMPT,
                "stream": False,
                "think": False,
                "num_ctx": 65536,
                "num_predict": 128,
                "temperature": 0,
                "seed": 42,
                "warm_requests": 3,
                "cold_definition": "Model unloaded through API; OS file caches are not cleared",
                "workload": "Direct Ollama generation, without Hermes tools, history or Telegram",
            },
            "samples": [asdict(sample) for sample in samples],
            "warm_median_tokens_per_second": statistics.median(sample.tokens_per_second for sample in warm),
            "warm_median_wall_seconds": statistics.median(sample.wall_seconds for sample in warm),
            "warm_min_tokens_per_second": min(sample.tokens_per_second for sample in warm),
            "warm_max_tokens_per_second": max(sample.tokens_per_second for sample in warm),
        }
        sys.stdout.write(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    finally:
        # Do not leave a benchmark model consuming memory after this command.
        with suppress(OSError, ValueError, http.client.HTTPException):
            post({"model": MODEL, "keep_alive": 0})


if __name__ == "__main__":
    main()
