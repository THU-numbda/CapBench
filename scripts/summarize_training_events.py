#!/usr/bin/env python3
"""Summarize best and final validation metrics from baseline TensorBoard runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


MAPE_TAGS = ("val/mare", "Comprehensive/MARE", "val_mare")
MSRE_TAGS = ("val/msre", "Comprehensive/MSRE", "val_msre", "val_loss")


def summarize_series(events: Iterable[Any]) -> dict[str, float | int]:
    values = list(events)
    if not values:
        raise ValueError("metric series is empty")
    best = min(values, key=lambda event: float(event.value))
    final = max(values, key=lambda event: int(event.step))
    return {
        "count": len(values),
        "best": float(best.value),
        "best_step": int(best.step),
        "final": float(final.value),
        "final_step": int(final.step),
    }


def _first_available_tag(tags: set[str], candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        if candidate in tags:
            return candidate
    raise KeyError(f"None of the expected metric tags are present: {candidates}")


def summarize_event_file(path: Path) -> dict[str, Any]:
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

    accumulator = EventAccumulator(str(path)).Reload()
    scalar_tags = set(accumulator.Tags().get("scalars", []))
    run_name = path.parent.name
    if "lightning_logs" in path.parts:
        run_name = path.parts[path.parts.index("lightning_logs") - 1]
    elif run_name == "tensorboard":
        run_name = path.parent.parent.name
    has_mape = not scalar_tags.isdisjoint(MAPE_TAGS)
    has_msre = not scalar_tags.isdisjoint(MSRE_TAGS)
    if not has_mape and not has_msre:
        return {
            "event_file": str(path),
            "run": run_name,
            "status": "waiting_for_metrics",
        }
    mape_tag = _first_available_tag(scalar_tags, MAPE_TAGS)
    msre_tag = _first_available_tag(scalar_tags, MSRE_TAGS)
    return {
        "event_file": str(path),
        "run": run_name,
        "mape_tag": mape_tag,
        "msre_tag": msre_tag,
        "mape": summarize_series(accumulator.Scalars(mape_tag)),
        "msre": summarize_series(accumulator.Scalars(msre_tag)),
    }


def find_event_files(paths: list[Path]) -> list[Path]:
    event_files: set[Path] = set()
    for path in paths:
        if path.is_file() and path.name.startswith("events.out.tfevents"):
            event_files.add(path.resolve())
        elif path.is_dir():
            event_files.update(
                candidate.resolve()
                for candidate in path.rglob("events.out.tfevents.*")
                if candidate.is_file()
            )
        else:
            raise FileNotFoundError(path)
    if not event_files:
        raise FileNotFoundError("No TensorBoard event files found")
    return sorted(event_files)


def print_markdown(summaries: list[dict[str, Any]]) -> None:
    print("| Run | Epochs | Best MAPE | Final MAPE | Best MSRE | Final MSRE |")
    print("| --- | ---: | ---: | ---: | ---: | ---: |")
    for summary in summaries:
        if summary.get("status") == "waiting_for_metrics":
            print(f"| {summary['run']} | waiting | — | — | — | — |")
            continue
        mape = summary["mape"]
        msre = summary["msre"]
        print(
            f"| {summary['run']} | {mape['count']} | "
            f"{100.0 * mape['best']:.4f}% (step {mape['best_step']}) | "
            f"{100.0 * mape['final']:.4f}% (step {mape['final_step']}) | "
            f"{msre['best']:.6f} | {msre['final']:.6f} |"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="+", help="Event files or run directories.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    args = parser.parse_args()

    summaries = [summarize_event_file(path) for path in find_event_files(args.paths)]
    if args.json:
        print(json.dumps(summaries, indent=2, sort_keys=True))
    else:
        print_markdown(summaries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
