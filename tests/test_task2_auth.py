from task2_mcp_gateway.gateway import role_from_authorization


def test_admin_token():
    assert role_from_authorization("Bearer admin-token") == "admin"


def test_viewer_token():
    assert role_from_authorization("Bearer viewer-token") == "viewer"


def test_invalid_token():
    assert role_from_authorization("Bearer nope") is None
