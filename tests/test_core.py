import os
import tempfile
from part4.memory import WorkingMemory
from part4.state_manager import TaskGraph
from part4.audit_logger import AuditLogger

def test_working_memory():
    wm = WorkingMemory()
    wm.set("t1", "k", 1)
    assert wm.get("t1", "k") == 1
    wm.clear("t1")
    assert wm.get("t1", "k") is None

def test_state_manager_and_rollback():
    tg = TaskGraph()
    tg.add_step("s1")
    rolled_back = {"ok": False}

    def rb():
        rolled_back["ok"] = True

    tg.register_rollback("s1", rb)
    tg.cancel()
    assert rolled_back["ok"] is True

def test_audit_logger_masks():
    path = os.path.join(tempfile.gettempdir(), "test_part4_audit.log")
    if os.path.exists(path):
        os.remove(path)
    logger = AuditLogger(path=path)
    payload = {"msisdn": "secret", "other": 1}
    entry = logger.write_entry("s1", {"op": "x"}, {"ok": True}, extra=payload)
    assert "masked_fields" in entry
    assert "msisdn" in entry["masked_fields"]

def test_audit_logger_inline_mask():
    path = os.path.join(tempfile.gettempdir(), "test_part4_audit2.log")
    if os.path.exists(path):
        os.remove(path)
    logger = AuditLogger(path=path)
    payload = {"note": "Contact: 1234567890"}
    entry = logger.write_entry("s2", {"op": "y"}, {"ok": True}, extra=payload)
    assert "masked_fields" in entry
    assert "inline_phone" in entry["masked_fields"]

if __name__ == "__main__":
    test_working_memory()
    test_state_manager_and_rollback()
    test_audit_logger_masks()
    print("All tests passed")
