class PolicyEngine:
    """Part 3: Deterministic Rule-Based Safety Core.
    
    Sole authority for ALLOW / ASK_CONFIRM / DENY decisions. Pure function.
    """

    def evaluate(self, step: dict, current_cell_value=None) -> dict:
        step_id = step.get("step_id")
        action_type = step.get("type")
        target = step.get("target", {})
        
        # 1. READ ACTIONS ARE ALLOWED
        if action_type == "read":
            return {
                "step_id": step_id,
                "decision": "ALLOW",
                "tier": "read-only",
                "reason": "Read-only operation on local file"
            }

        # 2. WRITE ACTIONS REQUIRE EVALUATION
        if action_type == "write":
            # Prompt-injection guardrail check
            if "delete" in str(step.get("value", "")).lower() or "shell" in str(target).lower():
                return {
                    "step_id": step_id,
                    "decision": "DENY",
                    "tier": "untrusted-instruction-injection",
                    "reason": "Action command derived from untrusted/injurious pattern"
                }

            # If target already has value -> Require user confirmation
            if current_cell_value is not None and str(current_cell_value).strip() != "":
                return {
                    "step_id": step_id,
                    "decision": "ASK_CONFIRM",
                    "tier": "reversible-write-overwrite",
                    "reason": f"Target location '{target.get('cell', 'field')}' currently contains a non-empty value ({current_cell_value})"
                }
            
            return {
                "step_id": step_id,
                "decision": "ALLOW",
                "tier": "reversible-write-empty",
                "reason": "Target cell/field is empty"
            }

        # 3. DESTRUCTIVE ACTIONS REQUIRE CONFIRMATION
        if action_type in ("delete", "clear"):
            return {
                "step_id": step_id,
                "decision": "ASK_CONFIRM",
                "tier": "destructive",
                "reason": "Destructive file or content deletion requested"
            }

        return {
            "step_id": step_id,
            "decision": "DENY",
            "tier": "unknown-action",
            "reason": f"Unrecognized action type '{action_type}'"
        }