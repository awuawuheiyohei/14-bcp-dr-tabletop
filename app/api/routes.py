"""
BCP DR Tabletop API Routes
- BIA Systems / Exercises / Responses / CAPs / Report / Audit
"""
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel, Field

from ..models.db import get_conn, init_db, row_to_dict, rows_to_dicts, write_audit
from ..models.bia import (
    TABLETOP_INJECTS, get_inject, score_response, cap_severity,
    determine_tier, rto_for_tier, rpo_for_tier, classify_system,
    compute_bia_portfolio_stats,
)
from ..models.seed import seed_all, _make_systems

router = APIRouter()


# ============================================
# Pydantic
# ============================================
class ResponseIn(BaseModel):
    inject_id: int = Field(..., ge=1, le=4)
    stakeholder: str
    decision_taken: str
    decision_correct: bool = True
    time_to_decide_min: int = Field(0, ge=0)
    notes: Optional[str] = ""


class CAPIn(BaseModel):
    finding: str
    owner: str
    action_plan: str
    due_date: str  # YYYY-MM-DD
    inject_id: Optional[int] = None
    framework_ref: Optional[str] = None


# ============================================
# Dashboard / BIA Portfolio
# ============================================
@router.get("/dashboard/summary")
async def dashboard_summary():
    init_db()
    conn = get_conn()
    n_systems = conn.execute("SELECT COUNT(*) FROM systems").fetchone()[0]
    n_t0 = conn.execute("SELECT COUNT(*) FROM systems WHERE tier='TIER_0'").fetchone()[0]
    n_t1 = conn.execute("SELECT COUNT(*) FROM systems WHERE tier='TIER_1'").fetchone()[0]
    n_t2 = conn.execute("SELECT COUNT(*) FROM systems WHERE tier='TIER_2'").fetchone()[0]

    n_ex = conn.execute("SELECT COUNT(*) FROM exercises").fetchone()[0]
    last_ex = conn.execute("SELECT * FROM exercises ORDER BY started_at DESC LIMIT 1").fetchone()
    last_ex_d = row_to_dict(last_ex) if last_ex else None

    n_caps_open = conn.execute("SELECT COUNT(*) FROM caps WHERE status='OPEN'").fetchone()[0]
    n_caps_critical = conn.execute(
        "SELECT COUNT(*) FROM caps WHERE status='OPEN' AND severity='CRITICAL'"
    ).fetchone()[0]
    by_cap_sev = rows_to_dicts(conn.execute(
        "SELECT severity, COUNT(*) as cnt FROM caps WHERE status='OPEN' GROUP BY severity"
    ).fetchall())
    by_unit = rows_to_dicts(conn.execute(
        "SELECT business_unit, COUNT(*) as cnt FROM systems GROUP BY business_unit ORDER BY cnt DESC"
    ).fetchall())

    total_hourly = conn.execute(
        "SELECT COALESCE(SUM(hourly_loss_usd), 0) FROM systems"
    ).fetchone()[0]

    return {
        "systems": n_systems,
        "by_tier": {"TIER_0": n_t0, "TIER_1": n_t1, "TIER_2": n_t2},
        "exercises": n_ex,
        "latest_exercise": last_ex_d,
        "caps_open": n_caps_open,
        "caps_critical_open": n_caps_critical,
        "by_cap_severity": by_cap_sev,
        "by_unit": by_unit,
        "total_hourly_loss_usd": round(total_hourly, 2),
        "worst_case_24h_loss_usd": round(total_hourly * 24, 2),
    }


# ============================================
# BIA: Systems
# ============================================
@router.get("/bia/systems")
async def list_systems(tier: Optional[str] = None,
                       business_unit: Optional[str] = None,
                       region: Optional[str] = None):
    init_db()
    conn = get_conn()
    sql = "SELECT * FROM systems WHERE 1=1"
    params = []
    if tier:
        sql += " AND tier=?"
        params.append(tier)
    if business_unit:
        sql += " AND business_unit=?"
        params.append(business_unit)
    if region:
        sql += " AND region=?"
        params.append(region)
    sql += " ORDER BY CASE tier WHEN 'TIER_0' THEN 0 WHEN 'TIER_1' THEN 1 ELSE 2 END, hourly_loss_usd DESC"
    rows = rows_to_dicts(conn.execute(sql, params).fetchall())
    return {"count": len(rows), "items": rows}


@router.get("/bia/systems/{system_id}")
async def get_system(system_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM systems WHERE system_id=?", (system_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"System not found: {system_id}")
    return row_to_dict(row)


@router.get("/bia/portfolio")
async def bia_portfolio():
    init_db()
    conn = get_conn()
    rows = rows_to_dicts(conn.execute("SELECT * FROM systems").fetchall())
    stats = compute_bia_portfolio_stats(rows)
    by_unit = {}
    for s in rows:
        bu = s.get("business_unit", "platform")
        by_unit.setdefault(bu, {"count": 0, "hourly_loss": 0.0, "tier_0_count": 0})
        by_unit[bu]["count"] += 1
        by_unit[bu]["hourly_loss"] += float(s.get("hourly_loss_usd", 0))
        if s.get("tier") == "TIER_0":
            by_unit[bu]["tier_0_count"] += 1
    return {
        "stats": stats,
        "by_unit": [{"business_unit": k, **v} for k, v in by_unit.items()],
    }


@router.post("/bia/reclassify/{system_id}")
async def reclassify(system_id: str, actor: str = "bia-committee"):
    """重新计算 tier + RTO/RPO（适用于系统重要性变化时）"""
    conn = get_conn()
    row = conn.execute("SELECT * FROM systems WHERE system_id=?", (system_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"System not found: {system_id}")
    d = row_to_dict(row)
    new_tier = determine_tier(d["hourly_loss_usd"], bool(d["contains_pci"]),
                              bool(d["regulatory_fine_risk"]))
    new_rto = rto_for_tier(new_tier)
    new_rpo = rpo_for_tier(new_tier)
    old_tier = d["tier"]
    conn.execute(
        "UPDATE systems SET tier=?, target_rto_hours=?, target_rpo_hours=? WHERE system_id=?",
        (new_tier, new_rto, new_rpo, system_id)
    )
    write_audit(conn, actor=actor, action="reclassify",
                entity_type="systems", entity_id=system_id,
                details={"old_tier": old_tier, "new_tier": new_tier})
    conn.commit()
    return {"system_id": system_id, "old_tier": old_tier, "new_tier": new_tier,
            "target_rto_hours": new_rto, "target_rpo_hours": new_rpo}


# ============================================
# Tabletop Scenarios (剧本 read-only)
# ============================================
@router.get("/scenarios/injects")
async def list_injects():
    return {"count": len(TABLETOP_INJECTS), "items": TABLETOP_INJECTS}


@router.get("/scenarios/injects/{inject_id}")
async def get_one_inject(inject_id: int):
    inj = get_inject(inject_id)
    if not inj:
        raise HTTPException(404, f"Inject not found: {inject_id}")
    return inj


# ============================================
# Exercises
# ============================================
@router.get("/exercises")
async def list_exercises(limit: int = Query(20, ge=1, le=100)):
    init_db()
    conn = get_conn()
    rows = rows_to_dicts(conn.execute(
        "SELECT * FROM exercises ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall())
    return {"count": len(rows), "items": rows}


@router.get("/exercises/{exercise_id}")
async def get_exercise(exercise_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM exercises WHERE exercise_id=?", (exercise_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"Exercise not found: {exercise_id}")
    d = row_to_dict(row)
    try:
        d["participants"] = json.loads(d["participants"]) if d["participants"] else []
    except Exception:
        d["participants"] = []
    return d


@router.post("/exercises/{exercise_id}/responses")
async def add_response(exercise_id: str, body: ResponseIn, actor: str = "facilitator"):
    conn = get_conn()
    if not conn.execute("SELECT 1 FROM exercises WHERE exercise_id=?", (exercise_id,)).fetchone():
        raise HTTPException(404, f"Exercise not found: {exercise_id}")
    inj = get_inject(body.inject_id)
    if not inj:
        raise HTTPException(400, f"Invalid inject_id: {body.inject_id}")

    sc = score_response(body.inject_id, body.decision_taken, body.time_to_decide_min,
                        body.decision_correct)
    cur = conn.execute(
        """INSERT INTO responses
           (exercise_id, inject_id, phase_title, stakeholder, decision_taken,
            decision_correct, score, time_to_decide_min, notes)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (exercise_id, body.inject_id, inj["phase_title"], body.stakeholder,
         body.decision_taken, int(bool(body.decision_correct)), sc["score"],
         body.time_to_decide_min,
         json.dumps({"breakdown": {"correctness": sc["correctness_pts"],
                                   "speed": sc["speed_pts"],
                                   "quality": sc["quality_pts"]}}, ensure_ascii=False))
    )
    write_audit(conn, actor=actor, action="add_response",
                entity_type="responses", entity_id=str(cur.lastrowid),
                details={"exercise_id": exercise_id, "inject_id": body.inject_id,
                         "score": sc["score"]})
    # 重算 overall_score
    rows = conn.execute(
        "SELECT AVG(score) FROM responses WHERE exercise_id=?", (exercise_id,)
    ).fetchone()
    if rows[0] is not None:
        overall = round(float(rows[0]) * 4, 2)  # 4 phases × 25
        conn.execute("UPDATE exercises SET overall_score=? WHERE exercise_id=?",
                     (overall, exercise_id))
    conn.commit()
    return {"response_id": cur.lastrowid, "score": sc["score"],
            "breakdown": {"correctness": sc["correctness_pts"],
                          "speed": sc["speed_pts"],
                          "quality": sc["quality_pts"]}}


@router.get("/exercises/{exercise_id}/scorecard")
async def exercise_scorecard(exercise_id: str):
    conn = get_conn()
    ex = conn.execute("SELECT * FROM exercises WHERE exercise_id=?",
                      (exercise_id,)).fetchone()
    if not ex:
        raise HTTPException(404, f"Exercise not found: {exercise_id}")
    responses = rows_to_dicts(conn.execute(
        "SELECT * FROM responses WHERE exercise_id=? ORDER BY inject_id, stakeholder",
        (exercise_id,)
    ).fetchall())
    caps = rows_to_dicts(conn.execute(
        "SELECT * FROM caps WHERE exercise_id=? ORDER BY severity, due_date",
        (exercise_id,)
    ).fetchall())

    by_phase = {1: [], 2: [], 3: [], 4: []}
    for r in responses:
        try:
            notes = json.loads(r.get("notes") or "{}")
        except Exception:
            notes = {}
        r["breakdown"] = notes.get("breakdown", {})
        by_phase[r["inject_id"]].append(r)
    phase_avg = {p: round(sum(x["score"] for x in xs) / max(1, len(xs)), 2)
                 for p, xs in by_phase.items()}
    return {
        "exercise": row_to_dict(ex),
        "responses": responses,
        "by_phase": phase_avg,
        "caps": caps,
        "caps_open": sum(1 for c in caps if c["status"] == "OPEN"),
        "caps_critical": sum(1 for c in caps if c["status"] == "OPEN" and c["severity"] == "CRITICAL"),
    }


# ============================================
# CAPs
# ============================================
@router.get("/caps")
async def list_caps(status: Optional[str] = "OPEN", severity: Optional[str] = None):
    init_db()
    conn = get_conn()
    sql = "SELECT * FROM caps WHERE 1=1"
    params = []
    if status:
        sql += " AND status=?"
        params.append(status)
    if severity:
        sql += " AND severity=?"
        params.append(severity)
    sql += " ORDER BY CASE severity WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 ELSE 2 END, due_date"
    rows = rows_to_dicts(conn.execute(sql, params).fetchall())
    return {"count": len(rows), "items": rows}


@router.post("/exercises/{exercise_id}/caps")
async def add_cap(exercise_id: str, body: CAPIn, actor: str = "facilitator"):
    conn = get_conn()
    if not conn.execute("SELECT 1 FROM exercises WHERE exercise_id=?", (exercise_id,)).fetchone():
        raise HTTPException(404, f"Exercise not found: {exercise_id}")
    # 自动分级（除非用户指定）
    sev = body.severity if hasattr(body, "severity") and body.severity else cap_severity(body.finding)
    # 生成 cap_id
    existing = conn.execute("SELECT COUNT(*) FROM caps").fetchone()[0]
    cap_id = f"CAP-{existing + 1:03d}"
    cur = conn.execute(
        """INSERT INTO caps
           (cap_id, exercise_id, inject_id, finding, severity,
            owner, action_plan, due_date, status, framework_ref)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (cap_id, exercise_id, body.inject_id, body.finding, sev,
         body.owner, body.action_plan, body.due_date, "OPEN",
         body.framework_ref or "")
    )
    write_audit(conn, actor=actor, action="add_cap",
                entity_type="caps", entity_id=cap_id,
                details={"exercise_id": exercise_id, "severity": sev})
    conn.commit()
    return {"cap_id": cap_id, "severity": sev, "status": "OPEN"}


@router.patch("/caps/{cap_id}")
async def update_cap(cap_id: str, status: str, actor: str = "cap-owner"):
    if status not in ("OPEN", "IN_PROGRESS", "CLOSED", "VERIFIED"):
        raise HTTPException(400, "Invalid status")
    conn = get_conn()
    row = conn.execute("SELECT * FROM caps WHERE cap_id=?", (cap_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"CAP not found: {cap_id}")
    now = datetime.now().isoformat()
    closed_at = now if status in ("CLOSED", "VERIFIED") else None
    verified_at = now if status == "VERIFIED" else None
    conn.execute(
        """UPDATE caps SET status=?, closed_at=COALESCE(?, closed_at),
           verified_at=COALESCE(?, verified_at) WHERE cap_id=?""",
        (status, closed_at, verified_at, cap_id)
    )
    write_audit(conn, actor=actor, action="update_cap",
                entity_type="caps", entity_id=cap_id, details={"status": status})
    conn.commit()
    return {"cap_id": cap_id, "status": status}


# ============================================
# Audit
# ============================================
@router.get("/audit")
async def list_audit(limit: int = Query(50, ge=1, le=500)):
    init_db()
    conn = get_conn()
    rows = rows_to_dicts(conn.execute(
        "SELECT * FROM audit_trail ORDER BY occurred_at DESC LIMIT ?", (limit,)
    ).fetchall())
    return {"count": len(rows), "items": rows}


# ============================================
# SOC 2 / ISO 27001 Audit Report
# ============================================
@router.get("/report/bcp")
async def report_bcp():
    init_db()
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    last_ex = conn.execute("SELECT * FROM exercises ORDER BY started_at DESC LIMIT 1").fetchone()
    last_ex_d = row_to_dict(last_ex) if last_ex else None

    # 各 phase 平均分（最近一次演练）
    phase_scores = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    if last_ex:
        rows = conn.execute(
            "SELECT inject_id, AVG(score) as avg_score, COUNT(*) as n FROM responses "
            "WHERE exercise_id=? GROUP BY inject_id",
            (last_ex["exercise_id"],)
        ).fetchall()
        for r in rows:
            phase_scores[r["inject_id"]] = round(r["avg_score"], 2)

    # CAPs by framework reference
    cap_by_framework = rows_to_dicts(conn.execute(
        "SELECT COALESCE(framework_ref, 'unmapped') as framework, severity, "
        "       COUNT(*) as cnt FROM caps WHERE status='OPEN' "
        "GROUP BY framework_ref, severity ORDER BY framework_ref"
    ).fetchall())

    # Systems by tier × region
    systems_matrix = rows_to_dicts(conn.execute(
        "SELECT tier, region, COUNT(*) as cnt FROM systems GROUP BY tier, region"
    ).fetchall())

    # 系统 + 最近恢复时间（mock）
    rto_breaches = conn.execute(
        """SELECT system_name, target_rto_hours, hourly_loss_usd FROM systems
           WHERE tier='TIER_0' AND target_rto_hours > 2"""
    ).fetchall()

    return {
        "report_date": today,
        "framework": "ISO 27001 A.5.29/A.5.30 + SOC 2 A1.2/A1.3 + PIPL/GDPR/PDPA",
        "latest_exercise": last_ex_d,
        "phase_scores": phase_scores,
        "cap_by_framework": cap_by_framework,
        "systems_matrix": systems_matrix,
        "tier0_rto_breaches": rows_to_dicts(rto_breaches),
    }


# ============================================
# Admin / Seed
# ============================================
@router.post("/admin/seed")
async def admin_seed(actor: str = "grc-team"):
    init_db()
    stats = seed_all(verbose=False)
    conn = get_conn()
    write_audit(conn, actor=actor, action="reseed",
                entity_type="system", entity_id="all", details=stats)
    conn.commit()
    return {"status": "ok", "stats": stats}