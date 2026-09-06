from pathlib import Path


def test_agent_roles_exist_and_write_records(tmp_path: Path) -> None:
    """Check that the agent roles exist and write inspectable records.

    Bounded repair is not a role anymore: its budget, loop detection, and
    policy short-circuit live in ``bayan.pipeline.repair.RepairService``
    and are covered by ``tests/test_repair.py``.
    """
    from bayan.agents import (
        PlannerAgent,
        RenderAgent,
        TemplateAgent,
        ValidationAgent,
    )

    run_dir = tmp_path / "run"
    roles = [
        PlannerAgent(run_dir),
        TemplateAgent(run_dir),
        RenderAgent(run_dir),
        ValidationAgent(run_dir),
    ]

    for agent in roles:
        res = agent.run({"test": "payload"})
        assert res["status"] == "success"
        assert res["role"] == agent.role_name
        assert "timestamp" in res
        assert res["next_action"] == "continue"
        assert (run_dir / "agent_records" / f"{agent.role_name}.json").exists()
