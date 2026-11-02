"""python -m app.catalog.cli INPUT.csv --provider rules --currency PLN --output DIR"""
import argparse
import json
from pathlib import Path
from .core import ContractError
from .pipeline import process, save_results
from .providers import AzureProvider, ProviderError, RuleProvider


def main():
    parser = argparse.ArgumentParser(description="ServicePromise local catalogue prototype; no payment")
    parser.add_argument("input", type=Path)
    parser.add_argument("--provider", choices=["rules", "azure"], default="rules")
    parser.add_argument("--currency", choices=["PLN", "USD", "EUR", "GBP"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()
    try:
        provider = AzureProvider(args.env_file) if args.provider == "azure" else RuleProvider()
        report, exported = process(args.input.read_bytes(), args.currency, provider)
        save_results(args.output, report, exported)
    except (ContractError, ProviderError, OSError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps({"provider": report["provider"], "excluded_before_quote": len(report["quote"]["excluded"]),
                      **report["settlement"], "elapsed_seconds": report["elapsed_seconds"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
