from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from .core import VERSION, Extraction, export_csv, preflight, settlement, validate
from .providers import ProviderError


def process(data: bytes, currency: str, provider, batch_size=5) -> tuple[dict, str]:
    started = time.monotonic()
    quote = preflight(data, currency)
    rows = quote["rows"]
    outcomes = {}
    for offset in range(0, len(rows), batch_size):
        pending = rows[offset:offset+batch_size]
        feedback = {}
        for attempt in (1, 2):
            try:
                extractions = provider.extract(pending, feedback)
                provider_failure = False
            except ProviderError:
                extractions = {}
                provider_failure = True
            retry = []
            for row in pending:
                candidate = extractions.get(row.source_id, Extraction(source_id=row.source_id))
                issues = ["provider_error"] if provider_failure else validate(row, candidate)
                previous = outcomes.get(row.source_id, {}).get("attempts", [])
                attempts = [*previous, {"attempt": attempt, "issues": issues, "extraction": candidate.model_dump()}]
                outcomes[row.source_id] = {"source_id": row.source_id,
                    "status": "accepted" if not issues else "undelivered",
                    "issues": issues, "extraction": candidate.model_dump(), "attempts": attempts}
                if issues:
                    retry.append(row)
                    feedback[row.source_id] = issues
            pending = retry
            if not pending:
                break
    results = [outcomes[r.source_id] for r in rows]
    exported = export_csv(rows, results)
    report = {"contract": VERSION, "provider": provider.name,
              "limitations": ["Local feasibility prototype; no payment is executed.",
                              "Acceptance checks a limited source grammar, not physical product truth.",
                              "Shopify import has not been tested in a store.",
                              "No human time-saving or willingness-to-pay study completed."],
              "quote": {k: v for k, v in quote.items() if k != "rows"},
              "source_rows": [r.model_dump() for r in rows], "results": results,
              "settlement": settlement(results), "provider_metrics": provider.metrics.copy(),
              "elapsed_seconds": round(time.monotonic()-started, 3),
              "prompt_version": "textiles-extract-v1",
              "export_sha256": hashlib.sha256(exported.encode()).hexdigest()}
    return report, exported


def save_results(directory: Path, report: dict, exported: str):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (directory / "products.csv").write_text(exported, encoding="utf-8")
