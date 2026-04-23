import os

API_KEY_ENV = "SCHEDULER_MCP_API_KEY"


def get_expected_api_key() -> str | None:
    return os.environ.get(API_KEY_ENV) or None


def validate_api_key(auth_header: str | None) -> bool:
    expected = get_expected_api_key()
    if not expected:
        return True

    if not auth_header:
        return False

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = auth_header

    return token == expected
