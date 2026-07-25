"""Build human-readable previews for each task type."""


def build_spreadsheet_preview(merge_result: dict, period: str, source: str, target: str) -> str:
    lines = [f"Merged {period} data from {source} into {target}", ""]
    lines.append(f"Added column {merge_result['new_column']}:")
    for m in merge_result["matched"]:
        lines.append(f"  row {m['row']}: {m['metric']} = {m['value']}")
    if merge_result["unmatched"]:
        lines.append("")
        lines.append(f"Not matched to an existing row (needs review): {', '.join(merge_result['unmatched'])}")
    lines.append("")
    lines.append(f"Output file: {merge_result['output_path']}")
    return "\n".join(lines)


def build_presentation_preview(result: dict) -> str:
    lines = [f"Updated presentation from {result['source']}", ""]
    if result["replacements"]:
        lines.append("Replacements made:")
        for r in result["replacements"]:
            lines.append(f"  slide {r['slide']}: {{{{ {r['placeholder']} }}}} → {r['value']}")
    else:
        lines.append("No {{placeholders}} matched. Available values:")
        for k, v in result["values_available"].items():
            lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append(f"Output file: {result['output_path']}")
    return "\n".join(lines)


def build_organise_preview(result: dict) -> str:
    lines = [f"Organised files by {result['rule']} into {result['dest_root']}", ""]
    for m in result["moves"]:
        if m["status"] == "copied":
            lines.append(f"  {m['source']} → {m['destination']}")
        else:
            lines.append(f"  {m['source']}: {m['status']}")
    return "\n".join(lines)


def build_comparison_preview(result: dict) -> str:
    lines = [f"Compared {len(result['sources'])} sources", ""]
    lines.append(f"Differences found: {result['disagreement_count']}")
    lines.append(f"Summary written to: {result['output_path']}")
    return "\n".join(lines)


def build_correction_preview(result: dict) -> str:
    lines = ["Document corrections", ""]
    if result["corrections_applied"]:
        for c in result["corrections_applied"]:
            lines.append(f"  '{c['before']}' → '{c['after']}'")
    else:
        lines.append("  No changes applied.")
    lines.append("")
    lines.append(f"Output file: {result['output_path']}")
    return "\n".join(lines)


def build_document_update_preview(result: dict) -> str:
    lines = [f"Updated document from {result['source']}", ""]
    if result["replacements"]:
        lines.append("Replacements made:")
        for r in result["replacements"]:
            lines.append(f"  {r['placeholder']} → {r['value']}")
    else:
        lines.append("No placeholders matched. Available values:")
        for k, v in result["values_available"].items():
            lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append(f"Output file: {result['output_path']}")
    return "\n".join(lines)

