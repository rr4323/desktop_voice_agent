"""Update a presentation using key values extracted from a source document."""
import os
import re

from pptx import Presentation
from pptx.util import Pt

from extractors.text_extractor import extract_text, extract_key_values


def _placeholder_pattern(label: str) -> re.Pattern:
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return re.compile(rf"\{{\{{\s*{re.escape(slug)}\s*\}}\}}", re.IGNORECASE)


def update_presentation(source_path: str, pptx_path: str, output_path: str | None = None) -> dict:
    source = extract_text(source_path)
    pairs = extract_key_values(source["text"])

    # Also pull financial metrics if source is PDF-like earnings report
    from extractors.pdf_extractor import extract_financials, METRIC_PATTERNS

    extra_pairs = []
    if source_path.lower().endswith(".pdf"):
        try:
            fin = extract_financials(source_path)
            for m in fin.get("metrics", []):
                if m["value"] is not None:
                    extra_pairs.append({"label": m["metric"], "value": str(m["value"])})
            if fin.get("period"):
                extra_pairs.append({"label": "period", "value": fin["period"]})
        except Exception:
            pass

    lookup = {}
    for p in pairs + extra_pairs:
        slug = re.sub(r"[^a-z0-9]+", "_", p["label"].lower()).strip("_")
        lookup[slug] = p["value"]

    prs = Presentation(pptx_path)
    replacements = []

    for slide_idx, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if not hasattr(shape, "text"):
                continue
            original = shape.text
            updated = original
            for slug, value in lookup.items():
                pattern = _placeholder_pattern(slug.replace("_", " "))
                alt_pattern = re.compile(rf"\{{\{{\s*{re.escape(slug)}\s*\}}\}}", re.IGNORECASE)
                if alt_pattern.search(updated):
                    updated = alt_pattern.sub(str(value), updated)
                    replacements.append({"slide": slide_idx, "placeholder": slug, "value": value})
            if updated != original:
                shape.text = updated

    out = output_path or pptx_path.replace(".pptx", "_updated.pptx")
    prs.save(out)

    return {
        "output_path": out,
        "replacements": replacements,
        "values_available": lookup,
        "source": source_path,
    }
