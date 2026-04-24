from mcp_server.resources.routine_resources import routine_config_guide


def test_routine_config_guide_resource_returns_markdown():
    content = routine_config_guide()

    assert "name: routine-config-reference" in content
    assert "## scheduler" in content
    assert "## model_config" in content
    assert "scheduler://guides/routine-config" not in content
