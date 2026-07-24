"""
Extracts financial metrics from a PDF into a normalized schema:
    {"metric": str, "value": float, "unit": "$M" | "%" | "$", "raw": str}

Strategy:
  1. Try text-layer extraction (pdfplumber) — cheap, no API call.
  2. If the page has no usable text (scanned/image PDF), this is where
     a Mistral OCR fallback plugs in — see extract_with_mistral_ocr() stub
     at the bottom. Not wired in yet since Phase 1's sample PDF has a text
     layer; wire it in Phase 5 per the execution plan.
"""
import re

# Known metric labels -> how to recognize them in text (order matters: more specific first)
METRIC_PATTERNS = [
    ("Revenue", r"revenue[:\s]+\$?([\d,.]+)\s*M", "$M"),
    ("Net Income", r"net income[:\s]+\$?([\d,.]+)\s*M", "$M"),
    ("EPS", r"eps[:\s]+\$?([\d.]+)", "$"),
    ("Operating Margin", r"operating margin[:\s]+([\d.]+)\s*%", "%"),
    ("Gross Margin", r"gross margin[:\s]+([\d.]+)\s*%", "%"),
]

PERIOD_PATTERN = r"(Q[1-4](?:\s*20\d{2})?|Fiscal Year \d{4})"


def has_text_layer(pdf_path: str) -> bool:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text() and page.extract_text().strip():
                return True
    return False


def extract_financials(pdf_path: str) -> dict:
    """Returns {"period": str|None, "metrics": [ {metric, value, unit, raw} ], "source": "text_layer"|"ocr"}"""
    import pdfplumber

    if not has_text_layer(pdf_path):
        return extract_with_mistral_ocr(pdf_path)

    full_text = ""
    tables_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            full_text += t + "\n"
            tbls = page.extract_tables() or []
            tables_data.extend(tbls)

    period_match = re.search(PERIOD_PATTERN, full_text, re.IGNORECASE)
    period = period_match.group(1).replace(" ", " ") if period_match else None

    metrics = []
    for name, pattern, unit in METRIC_PATTERNS:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            raw = m.group(0)
            value_str = m.group(1).replace(",", "")
            try:
                value = float(value_str)
            except ValueError:
                value = None
            metrics.append({"metric": name, "value": value, "unit": unit, "raw": raw})
        else:
            metrics.append({"metric": name, "value": None, "unit": unit, "raw": None})

    # Supplement metrics with table extraction if present
    for table in tables_data:
        if not table or len(table) < 2:
            continue
        header = [str(c or "").strip().lower() for c in table[0]]
        actual_idx = next((i for i, h in enumerate(header) if "actual" in h), 1 if len(header) > 1 else None)
        if actual_idx is None:
            continue
        for row in table[1:]:
            if len(row) > actual_idx and row[0] and row[actual_idx]:
                metric_name = str(row[0]).strip()
                val_str = str(row[actual_idx]).strip()
                # If metric was missing from regex matching, update it
                for m in metrics:
                    if m["value"] is None and m["metric"].lower() in metric_name.lower():
                        clean_val = re.sub(r"[^\d.]", "", val_str)
                        try:
                            m["value"] = float(clean_val)
                            m["raw"] = f"{metric_name} {val_str}"
                        except ValueError:
                            pass

    return {"period": period, "metrics": metrics, "source": "text_layer"}


def extract_pdf_metrics_map(pdf_path: str) -> dict:
    """Extract a comprehensive lookup map of metric keys and values from text & tables."""
    import pdfplumber

    lookup = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                if not table or len(table) < 2:
                    continue
                header = [str(c or "").strip().lower() for c in table[0]]
                actual_idx = next((i for i, h in enumerate(header) if "actual" in h), 1)

                for row in table[1:]:
                    if len(row) > actual_idx:
                        raw_metric = str(row[0] or "").strip()
                        val = str(row[actual_idx] or "").strip()
                        if not raw_metric or not val:
                            continue

                        clean_name = re.sub(r"\(.*?\)", "", raw_metric).strip()
                        slug = re.sub(r"[^a-z0-9]+", "_", clean_name.lower()).strip("_")

                        lookup[slug] = val
                        lookup[f"{slug}_value"] = val

                        # Semantic aliases for common document fields
                        if "revenue" in slug:
                            lookup["q3_revenue_value"] = val
                            lookup["q3_revenue"] = val
                            lookup["q3_total_revenue"] = val
                            lookup["revenue"] = val
                        elif "churn" in slug:
                            lookup["q3_churn_value"] = val
                            lookup["q3_churn"] = val
                            lookup["churn_rate"] = val
                            lookup["churn"] = val
                        elif "arpu" in slug:
                            lookup["arpu"] = val
                            lookup["q3_arpu"] = val
                        elif "availability" in slug:
                            lookup["network_availability"] = val
                            lookup["q3_network_availability"] = val

    # Also pull from extract_financials
    fin = extract_financials(pdf_path)
    for m in fin.get("metrics", []):
        if m["value"] is not None:
            slug = re.sub(r"[^a-z0-9]+", "_", m["metric"].lower()).strip("_")
            unit = m.get("unit") or ""
            val_fmt = f"{m['value']}{unit}"
            lookup.setdefault(slug, val_fmt)
            lookup.setdefault(f"{slug}_value", val_fmt)

    return lookup


def extract_with_mistral_ocr(pdf_path: str) -> dict:
    """
    Stub for Phase 5. When wired in, this calls Mistral's OCR endpoint on the
    rasterized pages and runs the same METRIC_PATTERNS regex pass over the
    returned text. Left unimplemented here so Phase 1 stays runnable without
    a Mistral API key.
    """
    raise NotImplementedError(
        "This PDF has no text layer. Mistral OCR fallback is planned for "
        "Phase 5 and needs MISTRAL_API_KEY set — not wired in yet."
    )


if __name__ == "__main__":
    import json
    import os

    samples = os.path.join(os.path.dirname(__file__), "..", "samples", "q3_earnings.pdf")
    result = extract_financials(os.path.abspath(samples))
    print(json.dumps(result, indent=2))
