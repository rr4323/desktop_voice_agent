import re

def is_number(v):
    try:
        float(str(v).replace("$", "").replace("%", "").replace(",", "").strip())
        return True
    except Exception:
        return False

def clean_number(v):
    return float(str(v).replace("$", "").replace("%", "").replace(",", "").strip())

def detect_anomaly(previous, current):
    """Flags suspicious deltas in KPI/numeric fields."""
    if previous is None or current is None:
        return False
    if not (is_number(previous) and is_number(current)):
        return False
    
    p = clean_number(previous)
    c = clean_number(current)
    
    if p == 0:
        return abs(c) > 1000000.0
    
    rel_change = abs((c - p) / p)
    # Flag if value jumped by > 1000% or absolute difference > 100,000
    if rel_change > 10.0 or abs(c - p) > 100000.0:
        return True
    return False

def verify_postcondition(action: dict, adapter) -> dict:
    """Re-reads target file via adapter to verify the write succeeded.
    
    Returns structured verification result with anomaly detection flags.
    """
    adapter_type = action.get("adapter") or action.get("target", {}).get("app")
    target = action.get("target", {})
    expected = str(action.get("expected")).strip() if action.get("expected") is not None else ""
    previous = action.get("previous")
    
    current = None
    postcondition_met = False
    anomaly_flag = False

    if adapter_type == "xlsx":
        res = adapter.read_cell(target["file"], target.get("sheet", "Sheet1"), target["cell"])
        current = res.get("value")
        current_str = str(current).strip() if current is not None else ""
        postcondition_met = (current_str == expected)
        anomaly_flag = detect_anomaly(previous, current)

    elif adapter_type == "pptx":
        slides = adapter.read_slides(target["file"])
        slide_num = target.get("slide", 1)
        found_slide = next((s for s in slides if s.get("slide") == slide_num), None)
        if found_slide:
            current = found_slide.get("text", "")
            postcondition_met = expected in current
        anomaly_flag = detect_anomaly(previous, expected)

    elif adapter_type == "pdf":
        # PDFs are read-only; verify presence of query
        pages = adapter.extract_text_with_provenance(target["file"])
        page_num = target.get("page")
        if page_num:
            pages = [p for p in pages if p["provenance"].get("page") == page_num]
        postcondition_met = any(expected in p.get("value", "") for p in pages)

    return {
        "verified": postcondition_met,
        "postcondition_met": postcondition_met,
        "anomaly_flag": anomaly_flag,
        "current_value": current
    }