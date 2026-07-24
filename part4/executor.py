import os

from part4.adapters.xlsx_adapter import XLSXAdapter
from part4.adapters.pdf_adapter import PDFAdapter
from part4.adapters.pptx_adapter import PPTXAdapter
from part4.memory import WorkingMemory
from part4.state_manager import TaskGraph
from part4.verification import verify_postcondition
from part4.audit_logger import AuditLogger

class ExecutionEngine:
    """The high-level controller that Orchestrators (Parts 1-3) call to execute planned steps."""

    def __init__(self, log_path="audit.log", state_path="task_state.json"):
        self.adapters = {
            "xlsx": XLSXAdapter(),
            "pdf": PDFAdapter(),
            "pptx": PPTXAdapter()
        }
        self.memory = WorkingMemory()
        self.state_manager = TaskGraph(storage_path=state_path)
        self.logger = AuditLogger(path=log_path)

    def execute_step(self, task_id: str, step: dict, decision: dict = None, transcript: str = "") -> dict:
        """Executes a single step, stores memory, verifies result, and logs audit trail."""
        step_id = str(step["step_id"])
        action_type = step.get("type")
        target = step.get("target", {})
        app = target.get("app")

        self.state_manager.add_step(step_id, meta=step)
        self.state_manager.update_status(step_id, "in_progress")

        adapter = self.adapters.get(app)
        if not adapter:
            self.state_manager.update_status(step_id, "failed")
            result = {"success": False, "error": f"Unsupported app '{app}'"}
            self.logger.write_entry(step_id, step, decision or {}, result, {"verified": False}, transcript)
            return result

        # Resolve value reference from Working Memory if present
        raw_val = step.get("value") or step.get("value_ref")
        resolved_value = self.memory.resolve_ref(task_id, raw_val)

        result = {}
        # 1. READ ACTION
        if action_type == "read":
            if app == "pdf":
                extracted = adapter.extract_text_with_provenance(target["file"])
                # Match query if present
                query = target.get("query", "").lower()
                matched = [e for e in extracted if query in e["value"].lower()] if query else extracted
                
                if matched:
                    res_item = matched[0]
                    result = {"success": True, "value": res_item["value"], "provenance": res_item["provenance"]}
                    self.memory.set(task_id, f"step_{step_id}.value", res_item["value"], res_item["provenance"])
                else:
                    result = {"success": False, "error": "query_not_found"}

            elif app == "xlsx":
                res = adapter.read_cell(target["file"], target.get("sheet", "Sheet1"), target["cell"])
                result = {"success": True, "value": res.get("value"), "provenance": target}
                self.memory.set(task_id, f"step_{step_id}.value", res.get("value"), target)

        # 2. WRITE ACTION
        elif action_type == "write":
            if app == "xlsx":
                res = adapter.write_cell(target["file"], target.get("sheet", "Sheet1"), target["cell"], resolved_value)
                result = res
                if res.get("success"):
                    self.state_manager.register_rollback(step_id, lambda: adapter.write_cell(target["file"], target.get("sheet", "Sheet1"), target["cell"], res["previous_value"]))
            elif app == "pptx":
                res = adapter.write_slide_text(target["file"], target.get("slide", 1), target.get("placeholder", ""), resolved_value)
                result = res

        # 3. VERIFICATION
        verification = verify_postcondition({
            "adapter": app,
            "target": target,
            "expected": resolved_value,
            "previous": result.get("previous_value")
        }, adapter)

        status = "done" if verification["verified"] else "failed"
        self.state_manager.update_status(step_id, status)

        # 4. AUDIT LOGGING
        self.logger.write_entry(
            step_id=step_id,
            action=step,
            decision=decision or {"decision": "ALLOW", "reason": "Deterministic execution"},
            result=result,
            verification=verification,
            transcript=transcript,
            extra={"task_id": task_id}
        )

        return {"result": result, "verification": verification}