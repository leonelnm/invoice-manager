from invoice_manager.security import fingerprint


def test_fingerprint_is_stable_and_distinguishes_operation_data():
    assert fingerprint("system-1", "001") == fingerprint("system-1", "001")
    assert fingerprint("system-1", "001") != fingerprint("system-2", "001")
    assert fingerprint("system-1", "001") != fingerprint("system-1", "002")
