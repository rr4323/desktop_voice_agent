"""Compare information across documents and create a summary."""
import os
from collections import defaultdict

from extractors.text_extractor import extract_text, extract_key_values
from extractors.pdf_extractor import extract_financials


def _values_from_file(path: str) -> dict[str, str]:
    data = {}
    if path.lower().endswith(".pdf"):
        try:
            fin = extract_financials(path)
            if fin.get("period"):
                data["Period"] = fin["period"]
            for m in fin.get("metrics", []):
                if m["value"] is not None:
                    unit = m.get("unit") or ""
                    data[m["metric"]] = f"{m['value']}{unit}"
        except Exception:
            pass

    extracted = extract_text(path)
    for pair in extract_key_values(extracted["text"]):
        data.setdefault(pair["label"], pair["value"])
    return data


def compare_and_summarize(sources: list[str], output_dir: str) -> dict:
    per_file = {os.path.basename(s): _values_from_file(s) for s in sources}

    all_labels = sorted({k for v in per_file.values() for k in v})
    comparisons = []
    for label in all_labels:
        row = {"label": label, "values": {}}
        vals = set()
        for name, fields in per_file.items():
            val = fields.get(label, "—")
            row["values"][name] = val
            if val != "—":
                vals.add(val)
        row["agreement"] = len(vals) <= 1
        comparisons.append(row)

    disagreements = [c for c in comparisons if not c["agreement"] and any(v != "—" for v in c["values"].values())]
    agreements = [c for c in comparisons if c["agreement"] and any(v != "—" for v in c["values"].values())]

    lines = ["# Cross-Document Comparison Summary", ""]
    lines.append(f"Sources: {', '.join(os.path.basename(s) for s in sources)}")
    lines.append("")
    lines.append("## Matching fields")
    if agreements:
        for c in agreements:
            val = next(v for v in c["values"].values() if v != "—")
            lines.append(f"- **{c['label']}**: {val} (consistent across sources)")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("## Differences / gaps")
    if disagreements:
        for c in disagreements:
            parts = [f"{k}: {v}" for k, v in c["values"].items() if v != "—"]
            lines.append(f"- **{c['label']}**: " + "; ".join(parts))
    else:
        lines.append("- No conflicting values detected.")

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "comparison_summary.md")
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    return {
        "output_path": out_path,
        "comparisons": comparisons,
        "disagreement_count": len(disagreements),
        "sources": sources,
    }
