import uuid
from part1 import ASRModule, TTSModule, ConfirmationParser
from part2 import TaskPlanner
from part3 import PolicyEngine
from part4 import ExecutionEngine

class AgentOrchestrator:
    """Master Orchestrator integrating Voice (P1), Planning (P2), Policy (P3), & Execution (P4)."""

    def __init__(self, log_path="audit.log", state_path="task_state.json"):
        # Initialize modules from all four parts
        self.asr = ASRModule()
        self.tts = TTSModule()
        self.confirmation_parser = ConfirmationParser()
        self.planner = TaskPlanner()
        self.policy_engine = PolicyEngine()
        self.execution_engine = ExecutionEngine(log_path=log_path, state_path=state_path)

    def execute_spoken_task(self, audio_or_transcript_input, environment_context: dict = None) -> dict:
        """End-to-end task execution pipeline."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        context = environment_context or {}

        # ---------------------------------------------------------------------
        # STAGE 1: Speech-To-Text (Part 1)
        # ---------------------------------------------------------------------
        print(">>> Stage 1: Capturing audio / transcribing...")
        asr_res = self.asr.transcribe(audio_or_transcript_input)
        transcript = asr_res["transcript"]
        print(f"    Transcript: '{transcript}' (Confidence: {asr_res['confidence']})")

        # ---------------------------------------------------------------------
        # STAGE 2: Task Planning via LLM (Part 2)
        # ---------------------------------------------------------------------
        print("\n>>> Stage 2: Generating task plan via LLM Task Planner...")
        plan = self.planner.plan(transcript, context=context)
        print(f"    Goal: {plan['goal']}")
        print(f"    Total Steps: {len(plan['steps'])}")

        # ---------------------------------------------------------------------
        # STAGE 3 & 4: Policy Engine Guardrails (P3) + Execution Engine (P4)
        # ---------------------------------------------------------------------
        results = []

        for step in plan["steps"]:
            step_id = str(step["step_id"])
            print(f"\n---> Processing Step {step_id} ({step['type']} on {step['target'].get('app')})")

            # A. Check existing target state (for write overwrites)
            current_target_val = None
            if step["type"] == "write" and step["target"].get("app") == "xlsx":
                read_check = self.execution_engine.adapters["xlsx"].read_cell(
                    step["target"]["file"], 
                    step["target"].get("sheet", "Sheet1"), 
                    step["target"]["cell"]
                )
                current_target_val = read_check.get("value")

            # B. Evaluate Policy Guardrail (Part 3)
            decision = self.policy_engine.evaluate(step, current_cell_value=current_target_val)
            print(f"    Policy Decision: {decision['decision']} ({decision['reason']})")

            # C. Handle Policy Decisions
            if decision["decision"] == "DENY":
                self.tts.speak(f"Request denied. {decision['reason']}")
                self.execution_engine.logger.write_entry(
                    step_id, step, decision, {"success": False, "error": "denied_by_policy"}, 
                    {"verified": False}, transcript
                )
                print("    Step ABORTED due to policy DENIAL.")
                break

            elif decision["decision"] == "ASK_CONFIRM":
                # Voice Confirmation Loop
                confirm_prompt = (
                    f"Cell {step['target'].get('cell')} currently contains '{current_target_val}'. "
                    f"Should I overwrite it?"
                )
                self.tts.speak(confirm_prompt)

                # Simulate / Listen for spoken approval
                user_reply = context.get("mock_user_confirmation", "yes go ahead")
                reply_transcript = self.asr.transcribe(user_reply)["transcript"]
                parsed_approval = self.confirmation_parser.parse(reply_transcript)

                if not parsed_approval["confirmed"]:
                    self.tts.speak("Action cancelled.")
                    self.execution_engine.state_manager.update_status(step_id, "failed")
                    print("    Step CANCELLED by user.")
                    break
                else:
                    print("    User CONFIRMED step execution.")

            # D. Execute Step via Part 4 Execution Engine
            exec_res = self.execution_engine.execute_step(
                task_id=task_id,
                step=step,
                decision=decision,
                transcript=transcript
            )
            results.append(exec_res)

            # E. Report Verified Result via TTS (Part 1)
            if exec_res["verification"]["postcondition_met"]:
                val = exec_res['result'].get('value') or exec_res['result'].get('new_value')
                self.tts.speak(f"Step {step_id} verified. Outcome: {val}")
            else:
                self.tts.speak(f"Step {step_id} execution failed verification.")

        print("\n========================================================")
        print("Task complete. Audit trail logged at:", self.execution_engine.logger.path)
        print("========================================================\n")
        return {"task_id": task_id, "results": results}