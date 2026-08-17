from pathlib import Path


def test_agent_roles_exist_and_write_records(tmp_path: Path) -> None:
    """Check that all 5 agent roles exist and write inspectable records."""
    from bayan.agents import (
        PlannerAgent,
        RenderAgent,
        RepairAgent,
        TemplateAgent,
        ValidationAgent,
    )

    run_dir = tmp_path / "run"
    roles = [
        PlannerAgent(run_dir),
        TemplateAgent(run_dir),
        RenderAgent(run_dir),
        ValidationAgent(run_dir),
        RepairAgent(run_dir),
    ]

    for agent in roles:
        res = agent.run({"test": "payload"})
        assert res["status"] == "success"
        assert res["role"] == agent.role_name
        assert "timestamp" in res
        assert res["next_action"] == "continue"
        assert (run_dir / "agent_records" / f"{agent.role_name}.json").exists()


def test_repair_agent_max_attempts(tmp_path: Path) -> None:
    """Check that RepairAgent caps attempts at max_attempts (default 2)."""
    from bayan.agents import RepairAgent

    run_dir = tmp_path / "run"
    repair = RepairAgent(run_dir=run_dir, max_attempts=2)

    res1 = repair.attempt_repair({"error": "render error"})
    assert res1["status"] == "attempted"

    res2 = repair.attempt_repair({"error": "render error"})
    assert res2["status"] == "attempted"

    res3 = repair.attempt_repair({"error": "render error"})
    assert res3["status"] == "exhausted"
    assert res3["next_action"] == "human_review"
    assert (run_dir / "review_packet.md").exists()


def test_loop_detection_triggers_human_review(tmp_path: Path) -> None:
    """Check that identical repeated attempts trigger loop detection and write review packet."""
    from bayan.agents import RepairAgent

    run_dir = tmp_path / "run"
    repair = RepairAgent(run_dir=run_dir)
    payload = {"code": "bad_code()"}

    res1 = repair.run_with_loop_check(payload)
    assert res1["status"] == "success"

    res2 = repair.run_with_loop_check(payload)
    assert res2["status"] == "loop_detected"
    assert res2["next_action"] == "human_review"
    assert (run_dir / "review_packet.md").exists()


def test_repair_agent_policy_failure_stops_immediately(tmp_path: Path) -> None:
    """Check that security/policy failure stops immediately without retries."""
    from bayan.agents import RepairAgent

    run_dir = tmp_path / "run"
    repair = RepairAgent(run_dir=run_dir)

    res = repair.attempt_repair({"category": "security", "message": "unauthorized access"})
    assert res["status"] == "policy_blocked"
    assert res["next_action"] == "human_review"
    assert (run_dir / "review_packet.md").exists()
