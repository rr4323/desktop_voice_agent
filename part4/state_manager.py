import json
import os
import logging

class TaskGraph:
    """State machine tracking step statuses and rollback functions.
    
    Persists state to local disk to allow pause, resume, and recovery after restart.
    """

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path
        self.steps = {}      # step_id -> {status, meta}
        self.rollbacks = {}  # step_id -> callable (in-memory)

        if self.storage_path and os.path.exists(self.storage_path):
            self.load_state()

    def add_step(self, step_id: str, meta: dict = None):
        self.steps[step_id] = {
            "status": "pending",
            "meta": meta or {}
        }
        self._auto_save()

    def update_status(self, step_id: str, status: str):
        if step_id not in self.steps:
            raise KeyError(f"Step {step_id} not found in TaskGraph.")
        valid_statuses = {"pending", "in_progress", "done", "failed", "paused"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of {valid_statuses}")
        
        self.steps[step_id]["status"] = status
        self._auto_save()

    def register_rollback(self, step_id: str, fn: callable):
        self.rollbacks[step_id] = fn

    def pause(self, step_id: str):
        self.update_status(step_id, "paused")

    def resume(self, step_id: str):
        self.update_status(step_id, "in_progress")

    def correct(self, step_id: str, new_target: dict = None):
        """Update step targets midway when requested by user instruction."""
        if step_id not in self.steps:
            raise KeyError(f"Step {step_id} not found in TaskGraph.")
        if new_target:
            self.steps[step_id]["meta"]["target"] = new_target
        self.update_status(step_id, "pending")

    def cancel(self):
        """Attempt rollback for executed steps and set status to failed."""
        for step_id, fn in self.rollbacks.items():
            try:
                fn()
            except Exception as e:
                logging.error(f"Rollback failed for step {step_id}: {e}")
            self.update_status(step_id, "failed")

    def save_state(self):
        if not self.storage_path:
            return
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump({"steps": self.steps}, f, indent=2)

    def load_state(self):
        if not self.storage_path or not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.steps = data.get("steps", {})
        except Exception as e:
            logging.error(f"Failed to load TaskGraph state: {e}")

    def _auto_save(self):
        if self.storage_path:
            self.save_state()