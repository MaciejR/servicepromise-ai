"""Compare rules with Azure against provisional labels, without claiming business validation."""
import argparse
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.catalog.core import COLUMNS
from app.catalog.pipeline import process, save_results
from app.catalog.providers import AzureProvider, RuleProvider

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["rules", "azure"], required=True)
    parser.add_argument("--split", choices=["development", "holdout", "all"], default="development")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    examples = ROOT / "examples" / "catalog"
    labels = {c["source_id"]: c for c in json.loads((examples / "expected.json").read_text())}
    labels = {key: c for key, c in labels.items() if args.split == "all" or c["split"] == args.split}
    decisions = []
    totals = {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "latency_seconds": 0.0}
    for group in ("simple", "messy", "edge"):
        rows = [r for r in csv.DictReader((examples / f"supplier_{group}.csv").open()) if r["source_id"] in labels]
        if not rows:
            continue
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        provider = AzureProvider(args.env_file) if args.provider == "azure" else RuleProvider()
        report, exported = process(buffer.getvalue().encode(), "PLN", provider)
        save_results(args.output / group, report, exported)
        by_id = {r["source_id"]: r for r in report["results"]}
        for r in report["quote"]["excluded"]:
            by_id[r["source_id"]] = {"source_id": r["source_id"], "status": "excluded", "issues": r["issues"]}
        for row in rows:
            cid = row["source_id"]
            result, expected = by_id[cid], labels[cid]["expected"]
            values = {key: (result.get("extraction", {}).get(key) or {}).get("value") for key in ("color", "material")}
            correct = result["status"] == expected["status"] and (result["status"] != "accepted" or all(values[k] == expected[k] for k in values))
            decisions.append({"source_id": cid, "group": group, "expected": expected, "actual_status": result["status"],
                              "values": values, "correct": correct, "issues": result["issues"]})
        for key in totals:
            totals[key] += report["provider_metrics"].get(key, 0)
        print(json.dumps({"group": group, "provider": args.provider, **report["settlement"]}), flush=True)
    complete = [d for d in decisions if d["expected"]["status"] == "accepted"]
    summary = {"provider": args.provider, "split": args.split, "case_count": len(decisions),
               "correct_decisions": sum(d["correct"] for d in decisions),
               "false_acceptances": sum(d["actual_status"] == "accepted" and not d["correct"] for d in decisions),
               "false_rejections": sum(d["actual_status"] != "accepted" for d in complete),
               "complete_cases": len(complete), "complete_correctly_accepted": sum(d["correct"] for d in complete),
               "metrics": totals, "decisions": decisions,
               "limitations": ["Synthetic assistant-authored cases and labels; no human review.",
                               "Holdout was not used for prompt tuning but is not independently authored.",
                               "No measured human time baseline, willingness to pay or store import.",
                               "No PayPal API call or actual refund was made."]}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in {"decisions", "limitations"}}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
