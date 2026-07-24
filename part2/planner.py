class TaskPlanner:
    """Part 2: LLM Task Planner Stub.
    
    Converts transcript into schema-valid stepwise ActionRequest JSON.
    """
    def __init__(self, model_name="qwen2.5:7b"):
        self.model_name = model_name

    def plan(self, transcript: str, context: dict = None) -> dict:
        """Emits a structured task plan array.
        
        Does NOT execute anything itself.
        """
        # =========================================================================
        # TODO [PART 2 DEVELOPER]: Replace below with Ollama / Local LLM call 
        # constrained by JSON Schema:
        # response = ollama.chat(model=self.model_name, messages=[...], format="json")
        # =========================================================================

        # Mock structured response for testing telecom PDF -> XLSX workflow:
        return {
            "goal": "Extract Q3 revenue from PDF report and copy into Excel KPI tracker",
            "steps": [
                {
                    "step_id": 1,
                    "type": "read",
                    "target": {
                        "app": "pdf",
                        "file": context.get("pdf_file", "network_report.pdf") if context else "network_report.pdf",
                        "query": "Q3 Revenue"
                    }
                },
                {
                    "step_id": 2,
                    "type": "write",
                    "target": {
                        "app": "xlsx",
                        "file": context.get("xlsx_file", "kpi_tracker.xlsx") if context else "kpi_tracker.xlsx",
                        "sheet": "Sheet1",
                        "cell": "B7"
                    },
                    "value_ref": "step_1.value",
                    "depends_on": [1]
                }
            ]
        }