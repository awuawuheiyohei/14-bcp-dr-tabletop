"""
BCP DR Tabletop - FastAPI route tests
- function-scoped fixture, reseed per test
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    db = ROOT / "data" / "bcp.db"
    for ext in ("", "-wal", "-shm"):
        p = Path(str(db) + ext)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
    with TestClient(app) as c:
        r = c.post("/api/admin/seed")
        assert r.status_code == 200, r.text
        yield c


# ============================================
# Health
# ============================================
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert d["service"] == "bcp-dr-tabletop"


# ============================================
# Seed
# ============================================
def test_admin_seed(client):
    r = client.post("/api/admin/seed")
    assert r.status_code == 200
    d = r.json()
    assert d["stats"]["systems"] == 10
    assert "exercise_id" in d["stats"]["exercise"]
    assert d["stats"]["exercise"]["responses"] >= 1


# ============================================
# Dashboard
# ============================================
def test_dashboard_summary(client):
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    d = r.json()
    assert d["systems"] == 10
    assert d["by_tier"]["TIER_0"] >= 1
    assert d["by_tier"]["TIER_1"] >= 1
    assert d["by_tier"]["TIER_2"] >= 1
    assert d["caps_open"] >= 1
    assert d["total_hourly_loss_usd"] > 0


# ============================================
# BIA
# ============================================
def test_list_systems(client):
    r = client.get("/api/bia/systems")
    assert r.status_code == 200
    assert r.json()["count"] == 10


def test_list_systems_tier0(client):
    r = client.get("/api/bia/systems?tier=TIER_0")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 3
    for s in items:
        assert s["tier"] == "TIER_0"
        assert s["target_rto_hours"] == 2
        assert s["target_rpo_hours"] == 0.0


def test_list_systems_filter_unit(client):
    r = client.get("/api/bia/systems?business_unit=marketing")
    assert r.status_code == 200
    for s in r.json()["items"]:
        assert s["business_unit"] == "marketing"


def test_get_system(client):
    r = client.get("/api/bia/systems/SYS-001")
    assert r.status_code == 200
    d = r.json()
    assert d["system_id"] == "SYS-001"
    assert d["contains_pci"] == 1
    assert d["tier"] == "TIER_0"


def test_get_system_404(client):
    r = client.get("/api/bia/systems/SYS-MISSING")
    assert r.status_code == 404


def test_bia_portfolio(client):
    r = client.get("/api/bia/portfolio")
    assert r.status_code == 200
    d = r.json()
    assert d["stats"]["total_systems"] == 10
    assert d["stats"]["worst_case_24h_loss_usd"] > 0
    assert len(d["by_unit"]) > 0


def test_reclassify(client):
    r = client.post("/api/bia/reclassify/SYS-007?actor=test",
                    json=None) if False else client.post(
        "/api/bia/reclassify/SYS-007", params={"actor": "test"}
    )
    assert r.status_code == 200
    d = r.json()
    assert d["system_id"] == "SYS-007"
    # SYS-007 hourly 2500 → TIER_2
    assert d["new_tier"] == "TIER_2"
    assert d["target_rto_hours"] == 24


def test_reclassify_404(client):
    r = client.post("/api/bia/reclassify/SYS-MISSING")
    assert r.status_code == 404


# ============================================
# Tabletop Scenarios
# ============================================
def test_list_injects(client):
    r = client.get("/api/scenarios/injects")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 4
    assert all("phase_title" in i for i in items)
    # 监管关键词覆盖（discussion_questions + regulatory_considerations 都扫）
    all_text = " ".join(
        i.get("regulatory_considerations", "") + " " +
        " ".join(i.get("discussion_questions", []))
        for i in items
    )
    assert "PIPL" in all_text or "GDPR" in all_text
    assert "SOC 2" in all_text


def test_get_inject(client):
    r = client.get("/api/scenarios/injects/2")
    assert r.status_code == 200
    assert r.json()["inject_id"] == 2


def test_get_inject_404(client):
    r = client.get("/api/scenarios/injects/99")
    assert r.status_code == 404


# ============================================
# Exercises
# ============================================
def test_list_exercises(client):
    r = client.get("/api/exercises")
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_get_exercise(client):
    ex_id = client.get("/api/exercises?limit=1").json()["items"][0]["exercise_id"]
    r = client.get(f"/api/exercises/{ex_id}")
    assert r.status_code == 200
    d = r.json()
    assert d["exercise_id"] == ex_id
    assert isinstance(d["participants"], list)


def test_get_exercise_404(client):
    r = client.get("/api/exercises/EX-MISSING")
    assert r.status_code == 404


def test_add_response(client):
    ex_id = client.get("/api/exercises?limit=1").json()["items"][0]["exercise_id"]
    r = client.post(
        f"/api/exercises/{ex_id}/responses",
        json={
            "inject_id": 4,
            "stakeholder": "DR Coordinator",
            "decision_taken": "Clean room recovery with immutable cold storage; forensic scan completed.",
            "decision_correct": True,
            "time_to_decide_min": 30,
        },
        params={"actor": "test"},
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert "score" in d
    assert d["breakdown"]["correctness"] == 15


def test_add_response_invalid_inject(client):
    ex_id = client.get("/api/exercises?limit=1").json()["items"][0]["exercise_id"]
    r = client.post(
        f"/api/exercises/{ex_id}/responses",
        json={"inject_id": 99, "stakeholder": "x", "decision_taken": "x",
              "decision_correct": True, "time_to_decide_min": 0},
    )
    # 422 (Pydantic) or 400 (manual validation) 都接受
    assert r.status_code in (400, 422)


def test_add_response_404_exercise(client):
    r = client.post(
        "/api/exercises/EX-MISSING/responses",
        json={"inject_id": 1, "stakeholder": "x", "decision_taken": "x",
              "decision_correct": True, "time_to_decide_min": 0},
    )
    assert r.status_code == 404


def test_exercise_scorecard(client):
    ex_id = client.get("/api/exercises?limit=1").json()["items"][0]["exercise_id"]
    r = client.get(f"/api/exercises/{ex_id}/scorecard")
    assert r.status_code == 200
    d = r.json()
    assert "by_phase" in d
    assert d["caps_open"] >= 1


# ============================================
# CAPs
# ============================================
def test_list_caps_default(client):
    r = client.get("/api/caps")
    assert r.status_code == 200
    items = r.json()["items"]
    # 默认 status=OPEN
    for c in items:
        assert c["status"] == "OPEN"


def test_list_caps_filter_severity(client):
    r = client.get("/api/caps?severity=CRITICAL")
    assert r.status_code == 200
    for c in r.json()["items"]:
        assert c["severity"] == "CRITICAL"


def test_add_cap(client):
    ex_id = client.get("/api/exercises?limit=1").json()["items"][0]["exercise_id"]
    r = client.post(
        f"/api/exercises/{ex_id}/caps",
        json={
            "finding": "No immutable backups in secondary region",
            "owner": "Cloud Ops",
            "action_plan": "Deploy S3 Object Lock Compliance Mode",
            "due_date": "2027-01-31",
            "framework_ref": "SOC 2 A1.2",
        },
        params={"actor": "test"},
    )
    assert r.status_code == 200, r.text
    d = r.json()
    # "no immutable" keyword → CRITICAL
    assert d["severity"] == "CRITICAL"
    assert d["status"] == "OPEN"


def test_update_cap(client):
    # 找一个 CAP
    caps = client.get("/api/caps").json()["items"]
    cap_id = caps[0]["cap_id"]
    r = client.patch(
        f"/api/caps/{cap_id}",
        params={"status": "CLOSED", "actor": "test"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "CLOSED"


def test_update_cap_invalid_status(client):
    caps = client.get("/api/caps").json()["items"]
    r = client.patch(
        f"/api/caps/{caps[0]['cap_id']}",
        params={"status": "BOGUS"},
    )
    assert r.status_code == 400


def test_update_cap_404(client):
    r = client.patch("/api/caps/CAP-MISSING", params={"status": "CLOSED"})
    assert r.status_code == 404


# ============================================
# Audit
# ============================================
def test_audit_trail(client):
    r = client.get("/api/audit?limit=20")
    assert r.status_code == 200
    items = r.json()["items"]
    # seed 至少写 1 条
    assert len(items) >= 1
    actions = {it["action"] for it in items}
    assert "reseed" in actions


# ============================================
# Report
# ============================================
def test_report_bcp(client):
    r = client.get("/api/report/bcp")
    assert r.status_code == 200
    d = r.json()
    assert "ISO 27001" in d["framework"]
    assert "SOC 2" in d["framework"]
    assert "phase_scores" in d
    # JSON 把 int keys 转 string "1"-"4"
    assert all(str(p) in d["phase_scores"] for p in (1, 2, 3, 4))


# ============================================
# Static Dashboard
# ============================================
def test_static_dashboard_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "BCP" in r.text or "bcp" in r.text.lower()