"""A versioned, deliberately narrow contract with deterministic acceptance rules."""
from __future__ import annotations

import csv
import hashlib
import html
import io
import re
import unicodedata
from collections import Counter
from decimal import Decimal, InvalidOperation
from pydantic import BaseModel, ConfigDict, Field

VERSION = "catalog-textiles-v1"
ASSESSED_VERSION = "catalog-textiles-v2"
COLUMNS = ["source_id", "sku", "name", "price", "currency", "supplier_text"]
MAX_ROWS, MAX_BYTES = 20, 256 * 1024
SERVICE_UNIT_CENTS = 100
ALIASES = {
    "color": {
        "blue": ["blue", "niebieski", "niebieska", "niebieskie", "niebieskim"],
        "red": ["red", "czerwony", "czerwona", "czerwone", "czerwonym"],
        "green": ["green", "zielony", "zielona", "zielone", "zielonym"],
        "white": ["white", "biały", "biała", "białe", "białym"],
        "black": ["black", "czarny", "czarna", "czarne", "czarnym"],
        "beige": ["beige", "beżowy", "beżowa", "beżowe", "beżowym"],
        "grey": ["grey", "gray", "szary", "szara", "szare", "szarym"],
    },
    "material": {
        "cotton": ["cotton", "bawełna", "bawełny", "bawełniany", "bawełniana"],
        "linen": ["linen", "len", "lnu", "lniany", "lniana"],
        "polyester": ["polyester", "poliester", "poliestru", "poliestrowy", "poliestrowa"],
        "wool": ["wool", "wełna", "wełny", "wełniany", "wełniana"],
    },
}
ANCHORS = {
    "color": r"(?:kolor(?: produktu)?|barwa|product colou?r|colou?r)\s*[:=]\s*([^.;\n]+)",
    "material": r"(?:materiał(?: produktu)?|skład|product material|material|composition)\s*[:=]\s*([^.;\n]+)",
}


class ContractError(ValueError):
    pass


class SourceRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_id: str
    sku: str
    name: str
    price: str
    currency: str
    supplier_text: str


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    value: str = Field(min_length=1, max_length=32)
    term: str = Field(min_length=1, max_length=80)
    quote: str = Field(min_length=1, max_length=500)


class Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    color: Evidence | None = None
    material: Evidence | None = None


def mentions(text: str, attribute: str) -> list[tuple[str, str, int, int]]:
    found = []
    for value, aliases in ALIASES[attribute].items():
        for alias in aliases:
            for match in re.finditer(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text, re.I):
                found.append((value, match.group(), match.start(), match.end()))
    return sorted(found, key=lambda m: m[2])


def candidates(text: str, attribute: str) -> tuple[set[str], list[tuple[str, str, int, int]]]:
    """Explicit product fields take precedence over incidental packaging references.

    Outside the supported field grammar, conflicting mentions fail closed. This
    checks a source contract, not the physical truth of a product claim.
    """
    anchored = []
    for match in re.finditer(ANCHORS[attribute], text, re.I):
        for value, term, start, end in mentions(match[1], attribute):
            anchored.append((value, term, match.start(1) + start, match.start(1) + end))
    found = anchored if anchored else mentions(text, attribute)
    return {m[0] for m in found}, found


def input_issues(raw: dict[str, str], currency: str) -> list[str]:
    issues = []
    for field in COLUMNS:
        value = raw.get(field, "")
        if not isinstance(value, str) or not value.strip():
            issues.append(f"missing_{field}")
        elif len(value) > (2000 if field == "supplier_text" else 160):
            issues.append(f"too_long_{field}")
        elif re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", value):
            issues.append(f"control_character_{field}")
    if raw.get("currency") != currency or currency not in {"PLN", "EUR", "USD", "GBP"}:
        issues.append("currency_mismatch")
    value = raw.get("price", "")
    try:
        price = Decimal(value)
        if not re.fullmatch(r"\d{1,8}(?:\.\d{1,2})?", value) or not price.is_finite() or price < 0:
            issues.append("invalid_price")
    except (InvalidOperation, ValueError):
        issues.append("invalid_price")
    # Quoting CSV does not neutralize spreadsheet formulas. Reject unsafe text
    # instead of adding apostrophes that silently change an authoritative SKU.
    for field in ["source_id", "sku", "name", "supplier_text"]:
        if raw.get(field, "").lstrip().startswith(("=", "+", "-", "@")):
            issues.append(f"spreadsheet_formula_{field}")
    return sorted(set(issues))


def preflight(data: bytes, currency: str) -> dict:
    if len(data) > MAX_BYTES:
        raise ContractError("File exceeds 256 KiB")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContractError("CSV must use UTF-8") from exc
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if reader.fieldnames != COLUMNS:
            raise ContractError("CSV headers must exactly match: " + ",".join(COLUMNS))
        rows = list(reader)
    except csv.Error as exc:
        raise ContractError("Malformed CSV") from exc
    if not 1 <= len(rows) <= MAX_ROWS:
        raise ContractError("A batch must contain 1–20 rows")
    for raw in rows:
        if None in raw or any(v is None for v in raw.values()):
            raise ContractError("A CSV row has the wrong number of columns")
    ids = Counter(r["source_id"] for r in rows)
    skus = Counter(r["sku"] for r in rows)
    accepted, rejected = [], []
    for index, raw in enumerate(rows, start=2):
        issues = input_issues(raw, currency)
        if ids[raw["source_id"]] > 1:
            issues.append("duplicate_source_id")
        if skus[raw["sku"]] > 1:
            issues.append("duplicate_sku")
        if issues:
            rejected.append({"line": index, "source_id": raw["source_id"], "issues": sorted(set(issues))})
        else:
            accepted.append(SourceRow(**raw))
    return {"rows": accepted, "excluded": rejected, "source_sha256": hashlib.sha256(data).hexdigest(),
            "quoted_cents": len(accepted) * SERVICE_UNIT_CENTS, "service_currency": "USD",
            "contract": VERSION, "product_currency": currency}


def validate(row: SourceRow, extraction: Extraction) -> list[str]:
    issues = []
    if extraction.source_id != row.source_id:
        issues.append("source_id_mismatch")
    for attribute in ALIASES:
        evidence = getattr(extraction, attribute)
        possible, found = candidates(row.supplier_text, attribute)
        # A single mentioned value is not necessarily an asserted product fact.
        if any(
            re.search(r"(?:\bnot\b|\bnie\b|\bbez\b|\bwithout\b|\bno\b)\W+(?:\w+\W+){0,2}$",
                      row.supplier_text[max(0, start-35):start], re.I)
            or re.match(r"[-‐‑–]free\b", row.supplier_text[end:end+6], re.I)
            for _, _, start, end in found
        ):
            issues.append(f"{attribute}_negated_or_unsupported_context")
        if len(possible) != 1:
            issues.append(f"{attribute}_{'ambiguous' if possible else 'unsupported_or_missing'}")
        if evidence is None:
            issues.append(f"{attribute}_missing_evidence")
            continue
        if evidence.value not in ALIASES[attribute]:
            issues.append(f"{attribute}_unsupported_value")
        if evidence.quote not in row.supplier_text or evidence.term not in evidence.quote:
            issues.append(f"{attribute}_ungrounded_quote")
        matches = mentions(evidence.term, attribute)
        if {m[0] for m in matches} != {evidence.value}:
            issues.append(f"{attribute}_invalid_normalization")
        quote_ranges = [(m.start(), m.end()) for m in re.finditer(re.escape(evidence.quote), row.supplier_text)]
        supported = any(value == evidence.value and term == evidence.term and
                        any(left <= start and end <= right for left, right in quote_ranges)
                        for value, term, start, end in found)
        if not supported or possible != {evidence.value}:
            issues.append(f"{attribute}_source_conflict")
    return sorted(set(issues))


def rule_extract(row: SourceRow) -> Extraction:
    """Context-aware deterministic baseline using exactly the validator's grammar."""
    result = {"source_id": row.source_id}
    for attribute in ALIASES:
        possible, found = candidates(row.supplier_text, attribute)
        if len(possible) == 1:
            value, term, _, _ = found[0]
            result[attribute] = Evidence(value=value, term=term, quote=term)
    return Extraction(**result)


def assess_source(data: bytes, currency: str) -> dict:
    """Conservative, model-free eligibility check before creating a new quote."""
    report = preflight(data, currency)
    eligible = []
    for row in report["rows"]:
        issues = validate(row, rule_extract(row))
        if issues:
            report["excluded"].append({"source_id": row.source_id,
                                       "stage": "source_review", "issues": issues})
        else:
            eligible.append(row)
    report.update(rows=eligible, quoted_cents=len(eligible) * SERVICE_UNIT_CENTS,
                  contract=ASSESSED_VERSION)
    return report


def settlement(results: list[dict]) -> dict:
    # All results are distinct, quoted input rows; upstream rejects duplicate IDs.
    if len({r["source_id"] for r in results}) != len(results):
        raise ContractError("Cannot settle duplicate items")
    delivered = sum(r["status"] == "accepted" for r in results)
    return {"simulation": True, "currency": "USD", "unit_cents": SERVICE_UNIT_CENTS,
            "quoted_cents": len(results) * SERVICE_UNIT_CENTS, "accepted_count": delivered,
            "undelivered_count": len(results) - delivered,
            "refund_eligible_cents": (len(results) - delivered) * SERVICE_UNIT_CENTS,
            "retained_cents": delivered * SERVICE_UNIT_CENTS, "payment_executed": False}


EXPORT_HEADERS = ["URL handle", "Title", "Description", "Tags", "Published on online store",
                  "Status", "SKU", "Price", "Option1 name", "Option1 value"]


def export_csv(rows: list[SourceRow], results: list[dict]) -> str:
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=EXPORT_HEADERS, lineterminator="\n")
    writer.writeheader()
    by_id = {r.source_id: r for r in rows}
    handles = set()
    for result in results:
        if result["status"] != "accepted":
            continue
        row = by_id[result["source_id"]]
        # Stable unique identifiers, independent of title transliteration collisions.
        slug = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", row.name).encode("ascii", "ignore").decode().lower()).strip("-") or "product"
        handle = slug[:70] + "-" + hashlib.sha256(row.source_id.encode()).hexdigest()[:12]
        if handle in handles:
            raise ContractError("Export handle collision")
        handles.add(handle)
        attrs = result["extraction"]
        writer.writerow({"URL handle": handle, "Title": row.name, "Description": html.escape(row.supplier_text),
                         "Tags": f"color:{attrs['color']['value']},material:{attrs['material']['value']}",
                         "Published on online store": "false", "Status": "draft", "SKU": row.sku,
                         "Price": row.price, "Option1 name": "Title", "Option1 value": "Default Title"})
    exported = out.getvalue()
    # Round trip validates preservation without float conversion or HTML rewriting.
    actual = list(csv.DictReader(io.StringIO(exported)))
    expected = [by_id[r["source_id"]] for r in results if r["status"] == "accepted"]
    if len(actual) != len(expected) or any(a["SKU"] != b.sku or a["Price"] != b.price for a, b in zip(actual, expected)):
        raise ContractError("Export failed authoritative-field round-trip validation")
    return exported
