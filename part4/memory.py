class WorkingMemory:
    """Task-scoped key-value store holding extracted values and provenance.
    
    Supports key resolution (e.g. resolving 'step_1.value' to the actual value).
    """

    def __init__(self):
        self._store = {}  # task_id -> {key: {"value": ..., "provenance": ...}}

    def set(self, task_id: str, key: str, value: str, provenance: dict = None):
        """Store a value with provenance metadata."""
        if task_id not in self._store:
            self._store[task_id] = {}
        self._store[task_id][key] = {
            "value": value,
            "provenance": provenance or {}
        }

    def get(self, task_id: str, key: str, default=None):
        """Retrieve stored record containing value and provenance."""
        return self._store.get(task_id, {}).get(key, default)

    def get_value(self, task_id: str, key: str, default=None):
        """Convenience method to return just the stored value string/number."""
        record = self.get(task_id, key)
        if isinstance(record, dict) and "value" in record:
            return record["value"]
        return default if default is not None else key

    def resolve_ref(self, task_id: str, value_or_ref: str):
        """If value_or_ref points to a stored step key (e.g. 'step_1.value'), resolve it."""
        if isinstance(value_or_ref, str) and value_or_ref in self._store.get(task_id, {}):
            return self.get_value(task_id, value_or_ref)
        return value_or_ref

    def clear(self, task_id: str):
        """Clear task context upon completion or cancellation."""
        if task_id in self._store:
            del self._store[task_id]