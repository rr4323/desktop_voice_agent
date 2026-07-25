"""CLI entry point for Voice-Controlled Desktop Agent & docuHandlers.

Usage:
    python main.py --prompt "..." --files file1.csv file2.xlsx
"""
import argparse
import os
from dotenv import load_dotenv

load_dotenv()

from components.c13_orchestrator.src.orchestrator import run_task


def find_matching_files(prompt: str, explicit_files: list[str]) -> list[str]:
    """Discover workspace files and match keywords in prompt if explicit files missing."""
    open_files = [os.path.abspath(f) if os.path.exists(f) else f for f in explicit_files]

    # Search workspace directories for candidates
    candidate_paths = []
    search_dirs = [os.getcwd(), os.path.join(os.getcwd(), "workspace_files"), os.path.join(os.getcwd(), "docuHandlers", "samples")]

    exts = (".csv", ".xlsx", ".pdf", ".pptx", ".docx")
    for d in search_dirs:
        if os.path.exists(d):
            for name in os.listdir(d):
                if name.endswith(exts) and not name.endswith(".bak"):
                    candidate_paths.append(os.path.join(d, name))

    # Match keywords from prompt
    prompt_words = [w.strip(".,'\"()").lower() for w in prompt.split() if len(w.strip(".,'\"()")) > 2]

    scored = []
    for path in set(candidate_paths):
        basename = os.path.basename(path).lower()
        score = sum(1 for w in prompt_words if w in basename)
        if score > 0:
            scored.append((score, path))

    # Sort by highest keyword match score
    scored.sort(key=lambda x: x[0], reverse=True)
    matched_paths = [p for s, p in scored]

    # Combine explicit files and top matched files
    combined = list(open_files)
    for p in matched_paths:
        if p not in combined:
            combined.append(p)

    # Fallback: if open_files still empty, include all candidate workspace files
    if not combined and candidate_paths:
        combined = candidate_paths

    return combined


def main():
    parser = argparse.ArgumentParser(description="Voice-Controlled Desktop Agent & docuHandlers CLI")
    parser.add_argument("--prompt", required=True, help="Task prompt instruction")
    parser.add_argument("--files", nargs="*", default=[], help="List of target input files")
    parser.add_argument("--no-auto-confirm", action="store_true", help="Do not auto-confirm ASK_CONFIRM prompts")

    args = parser.parse_args()

    open_files = find_matching_files(args.prompt, args.files)

    print(f"📋 Prompt: {args.prompt}")
    print(f"📁 Target Files: {open_files}")

    request = {
        "transcript": args.prompt,
        "context": {
            "open_files": open_files,
            "working_memory": {},
        },
        "auto_confirm": not args.no_auto_confirm,
    }

    output = run_task(request)
    print("\n" + "=" * 50)
    print("⚙️ Execution Result:")
    print("=" * 50)
    print(f"Status: {output.get('status')}")
    print(f"Response: {output.get('final_text')}")
    if output.get("audit_trail"):
        print("\n📜 Audit Trail:")
        for log in output["audit_trail"]:
            print(f"  - {log}")


if __name__ == "__main__":
    main()
