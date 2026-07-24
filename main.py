import os
import tempfile
from openpyxl import Workbook
from orchestrator import AgentOrchestrator

def setup_mock_environment():
    """Generates dummy files required for the test commands to execute without crashing."""
    temp_dir = tempfile.gettempdir()
    
    # 1. Create a sample XLSX file
    xlsx_path = os.path.join(temp_dir, "kpi_tracker.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws["B7"] = "1.8M"  # Pre-existing value to test the ASK_CONFIRM overwrite rule
    wb.save(xlsx_path)

    # 2. Create a sample PDF file
    pdf_path = os.path.join(temp_dir, "network_report.pdf")
    if not os.path.exists(pdf_path):
        with open(pdf_path, "wb") as f:
            # Minimal mock PDF byte structure for testing
            f.write(b"%PDF-1.4\n%Mock telecom content: Q3 Revenue 2.4M\n%%EOF")

    return pdf_path, xlsx_path

def main():
    print("=== INITIALIZING ENVIRONMENT ===")
    pdf_file, xlsx_file = setup_mock_environment()
    print(f"Mock files created at:\n - {xlsx_file}\n - {pdf_file}\n")

    agent = AgentOrchestrator(
        log_path=os.path.join(tempfile.gettempdir(), "audit_full_agent.log"),
        state_path=os.path.join(tempfile.gettempdir(), "state_full_agent.json")
    )

    print("=== BATCH PROCESSING TEXT DATA ===")
    
    # 1. Read the text data provided by the Part 1 developer
    commands_file = "sample_commands.txt" 
    
    if os.path.exists(commands_file):
        with open(commands_file, "r") as f:
            commands = [line.strip() for line in f if line.strip()]
    else:
        print(f"File '{commands_file}' not found. Using fallback commands.")
        # Fallback to a hardcoded list if the file isn't there yet
        commands = [
            "Pull the Q3 revenue total from the network report and put it into the KPI tracker."
        ]

    # 2. Loop through each text command and feed it directly into the orchestrator
    for i, spoken_text in enumerate(commands, start=1):
        print(f"\n--- Executing Task {i}: '{spoken_text}' ---")
        
        # We simulate the user saying "yes" if the policy engine asks for confirmation
        context = {
            "mock_user_confirmation": "yes, approve",
            "pdf_file": pdf_file,
            "xlsx_file": xlsx_file
        }

        # Notice we are passing the TEXT directly, bypassing the need for audio
        agent.execute_spoken_task(audio_or_transcript_input=spoken_text, environment_context=context)

if __name__ == "__main__":
    main()