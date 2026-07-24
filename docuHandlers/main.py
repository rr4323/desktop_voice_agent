"""
Document handler orchestrator.

Usage examples:
  python main.py --prompt "Locate information in the PDF and enter it into the spreadsheet" \\
      --files samples/q3_earnings.pdf samples/financials.xlsx

  python main.py --prompt "Update the presentation using information from the earnings report" \\
      --files samples/q3_earnings.pdf samples/deck.pptx

  python main.py --prompt "Organise these files by type into separate folders" \\
      --files samples/q3_earnings.pdf samples/financials.xlsx

  python main.py --prompt "Compare information across these documents and create a summary" \\
      --files samples/q3_earnings.pdf samples/financials.xlsx

  python main.py --prompt "Correct spelling errors while preserving formatting" \\
      --files samples/report.docx

  # Mid-instruction change / cancel (uses session from prior run):
  python main.py --session abc12345 --prompt "Actually, cancel that"
  python main.py --session abc12345 --prompt "Instead, compare the documents and summarize" \\
      --files samples/q3_earnings.pdf samples/financials.xlsx
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from orchestrator.intent_parser import parse_intent
from orchestrator.router import run_task
from orchestrator import session as session_store


def _resolve_files(files: list[str], working_dir: str) -> list[str]:
    resolved = []
    base_dir = os.path.dirname(__file__)
    for f in files:
        if os.path.isabs(f) and os.path.exists(f):
            resolved.append(f)
        elif os.path.exists(f):
            resolved.append(os.path.abspath(f))
        elif os.path.exists(os.path.join(working_dir, f)):
            resolved.append(os.path.abspath(os.path.join(working_dir, f)))
        elif os.path.exists(os.path.join(working_dir, os.path.basename(f))):
            resolved.append(os.path.abspath(os.path.join(working_dir, os.path.basename(f))))
        elif os.path.exists(os.path.join(base_dir, os.path.basename(f))):
            resolved.append(os.path.abspath(os.path.join(base_dir, os.path.basename(f))))
        else:
            resolved.append(os.path.join(working_dir, f))
    return resolved



def run(
    prompt: str,
    files: list[str],
    working_dir: str,
    session_id: str | None = None,
    replacements: list[str] | None = None,
    proceed_on_clarify: bool = False,
) -> dict:
    base_dir = os.path.dirname(__file__)
    files = _resolve_files(files, working_dir)

    # Handle session continuation
    if session_id:
        existing = session_store.load_session(base_dir, session_id)
        if existing is None:
            return {"status": "refuse", "message": f"Unknown session: {session_id}"}
        if existing.get("status") == "cancelled":
            return {"status": "cancelled", "message": existing.get("cancel_reason", "Task was cancelled.")}
        if existing.get("status") == "done":
            return {"status": "done", "message": "Session already completed.", "result": existing.get("result")}
        if not files:
            files = _resolve_files(existing.get("files", []), working_dir)

    intent = parse_intent(prompt, files)
    log = [{"stage": "intent_parser", "result": intent}]

    if intent["task_type"] == "cancel":
        if session_id:
            session_store.cancel_session(base_dir, session_id, intent.get("reason", "Cancelled."))
            return {"status": "cancelled", "message": "Task cancelled.", "log": log, "session_id": session_id}
        return {"status": "clarify", "message": "Nothing to cancel — start a task first or pass --session.", "log": log}

    if intent["task_type"] == "change":
        intent = {**intent, "task_type": intent["new_task_type"]}

    if session_id:
        session_store.update_session(base_dir, session_id, prompt, intent, files)
    elif files or intent.get("decision") == "clarify":
        session_id = session_store.create_session(base_dir, prompt, files, intent)

    if intent["decision"] == "clarify":
        return {"status": "clarify", "message": intent["reason"], "log": log, "intent": intent, "session_id": session_id}

    if intent["decision"] == "refuse":
        return {"status": "refuse", "message": intent["reason"], "log": log, "intent": intent, "session_id": session_id}

    result = run_task(intent, prompt, working_dir, replacements=replacements)

    if result["status"] == "clarify" and proceed_on_clarify:
        result["status"] = "done"
        result["message"] = result.get("message", "") + " (proceeded with --yes)"

    if result["status"] == "done":
        session_store.complete_session(base_dir, session_id, result)

    result["session_id"] = session_id
    result["log"] = log + result.get("log", [])
    result["intent"] = intent
    return result


def main():
    parser = argparse.ArgumentParser(description="Document handler orchestrator")
    parser.add_argument("--prompt", "-p", required=True, help="Natural-language task description")
    parser.add_argument("--files", "-f", nargs="*", default=[], help="Input files (paths)")
    parser.add_argument("--dir", default="samples", help="Working directory for relative paths")
    parser.add_argument("--session", "-s", help="Continue or modify an existing session")
    parser.add_argument("--replacements", nargs="*", help="Explicit corrections as old=new (for doc fix)")
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    parser.add_argument("--yes", action="store_true", help="Proceed when confidence gate returns clarify")
    args = parser.parse_args()

    working_dir = args.dir
    if not os.path.isabs(working_dir):
        working_dir = os.path.join(os.path.dirname(__file__), working_dir)

    files = _resolve_files(args.files, working_dir)

    result = run(
        prompt=args.prompt,
        files=files,
        working_dir=working_dir,
        session_id=args.session,
        replacements=args.replacements,
        proceed_on_clarify=args.yes,
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    print(f"\nstatus: {result['status']}")
    if result.get("session_id"):
        print(f"session: {result['session_id']}")
    print()
    if result["status"] == "done":
        print(result.get("preview", ""))
        if result.get("output_file"):
            print(f"\nOutput: {result['output_file']}")
    else:
        print(result.get("message", ""))


if __name__ == "__main__":
    main()
