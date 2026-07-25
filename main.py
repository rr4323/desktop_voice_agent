"""CLI entry point for Voice-Controlled Desktop Agent & docuHandlers.

Usage:
    python main.py --prompt "..." --files file1.csv file2.xlsx
"""
import argparse
import os
from dotenv import load_dotenv

load_dotenv()

from components.c13_orchestrator.src.orchestrator import run_task


def main():
    parser = argparse.ArgumentParser(description="Voice-Controlled Desktop Agent & docuHandlers CLI")
    parser.add_argument("--prompt", required=True, help="Task prompt instruction")
    parser.add_argument("--files", nargs="*", default=[], help="List of target input files")
    parser.add_argument("--no-auto-confirm", action="store_true", help="Do not auto-confirm ASK_CONFIRM prompts")

    args = parser.parse_args()

    open_files = [os.path.abspath(f) if os.path.exists(f) else f for f in args.files]

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
