"""The live API returns task errors in several shapes; the parser must
survive all of them (a crashing error handler once masked a real face-check
failure behind \"'str' object has no attribute 'get'\")."""

from drape.api.youcam_client import task_error


def test_error_as_bare_code_string():
    e = task_error({"task_status": "error", "error": "error_src_face_too_small"})
    assert str(e) == "error_src_face_too_small"
    assert e.error_code == "error_src_face_too_small"


def test_error_as_plain_message_string():
    e = task_error({"task_status": "error", "error": "engine exploded"})
    assert str(e) == "engine exploded"
    assert e.error_code is None


def test_error_as_dict():
    e = task_error({"task_status": "error", "error": {"message": "bad pose", "error_code": "error_pose"}})
    assert str(e) == "bad pose"
    assert e.error_code == "error_pose"


def test_error_null_with_sibling_code():
    e = task_error({"task_status": "error", "error": None, "error_code": "error_lighting_dark"})
    assert str(e) == "task failed"
    assert e.error_code == "error_lighting_dark"
