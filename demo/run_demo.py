import os
import tempfile
from openpyxl import Workbook
from part4.executor import ExecutionEngine

def run_integration_demo():
    print("=== Running Integration Demo ===")
    
    # 1. Setup sample file
    tmp_xlsx = os.path.join(tempfile.gettempdir(), "network_kpi.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws["B7"] = "1.8M"
    wb.save(tmp_xlsx)

    # 2. Instantiate Execution Engine
    engine = ExecutionEngine(
        log_path=os.path.join(tempfile.gettempdir(), "audit_demo.log"),
        state_path=os.path.join(tempfile.gettempdir(), "state_demo.json")
    )

    task_id = "task_telecom_001"
    transcript = "update the kpi tracker cell B7 with 2.4M"

    # Step 1: Write action
    step = {
        "step_id": 2,
        "type": "write",
        "target": {"app": "xlsx", "file": tmp_xlsx, "sheet": "Sheet1", "cell": "B7"},
        "value": "2.4M"
    }

    decision = {
        "decision": "ASK_CONFIRM",
        "reason": "Target cell B7 currently contains a non-empty value (1.8M)",
        "tier": "reversible-write-overwrite"
    }

    # Execute
    res = engine.execute_step(task_id, step, decision, transcript)

    print("Execution Output:", res)
    print("Audit Log generated at:", engine.logger.path)
    print("State saved at:", engine.state_manager.storage_path)

if __name__ == "__main__":
    run_integration_demo()