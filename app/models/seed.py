"""Seed: 10 mock systems (BIA) + 1 演练场次 + 4 phase 演示响应 + 5 mock CAPs"""
import json
from datetime import datetime, timezone, timedelta

from .db import get_conn, init_db
from .bia import determine_tier, rto_for_tier, rpo_for_tier, TABLETOP_INJECTS, score_response, cap_severity


# ============================================
# 10 Mock Systems
# ============================================
def _make_systems():
    today = datetime.now(timezone.utc)
    profiles = [
        # Tier 0
        {"system_id": "SYS-001", "system_name": "TripBiz-Payment-Gateway",
         "business_unit": "FinTech", "hourly_loss_usd": 80000.0,
         "contains_pci": 1, "contains_pii": 1, "regulatory_fine_risk": 1,
         "region": "apac", "data_classification": "RESTRICTED",
         "owner_email": "payments-lead@tripbiz.com"},
        {"system_id": "SYS-002", "system_name": "Booking-Central-DB",
         "business_unit": "platform", "hourly_loss_usd": 65000.0,
         "contains_pci": 0, "contains_pii": 1, "regulatory_fine_risk": 1,
         "region": "apac", "data_classification": "RESTRICTED",
         "owner_email": "platform-arch@tripbiz.com"},
        {"system_id": "SYS-003", "system_name": "Identity-Auth-Service",
         "business_unit": "platform", "hourly_loss_usd": 52000.0,
         "contains_pci": 0, "contains_pii": 1, "regulatory_fine_risk": 1,
         "region": "global", "data_classification": "RESTRICTED",
         "owner_email": "iam-arch@tripbiz.com"},
        # Tier 1
        {"system_id": "SYS-004", "system_name": "Customer-Portal-Web",
         "business_unit": "growth", "hourly_loss_usd": 18000.0,
         "contains_pci": 0, "contains_pii": 1, "regulatory_fine_risk": 0,
         "region": "global", "data_classification": "CONFIDENTIAL",
         "owner_email": "web-arch@tripbiz.com"},
        {"system_id": "SYS-005", "system_name": "Mobile-API-Gateway",
         "business_unit": "mobile", "hourly_loss_usd": 22000.0,
         "contains_pci": 0, "contains_pii": 1, "regulatory_fine_risk": 0,
         "region": "apac", "data_classification": "CONFIDENTIAL",
         "owner_email": "mobile-lead@tripbiz.com"},
        {"system_id": "SYS-006", "system_name": "Hotel-Inventory-Sync",
         "business_unit": "supply", "hourly_loss_usd": 15000.0,
         "contains_pci": 0, "contains_pii": 0, "regulatory_fine_risk": 1,
         "region": "emea", "data_classification": "CONFIDENTIAL",
         "owner_email": "supply-arch@tripbiz.com"},
        # Tier 2
        {"system_id": "SYS-007", "system_name": "BI-Reporting-DWH",
         "business_unit": "marketing", "hourly_loss_usd": 2500.0,
         "contains_pci": 0, "contains_pii": 0, "regulatory_fine_risk": 0,
         "region": "us", "data_classification": "INTERNAL",
         "owner_email": "bi-arch@tripbiz.com"},
        {"system_id": "SYS-008", "system_name": "Internal-Wiki",
         "business_unit": "people-ops", "hourly_loss_usd": 500.0,
         "contains_pci": 0, "contains_pii": 0, "regulatory_fine_risk": 0,
         "region": "global", "data_classification": "INTERNAL",
         "owner_email": "peopleops@tripbiz.com"},
        {"system_id": "SYS-009", "system_name": "Dev-Staging-Cluster",
         "business_unit": "engineering", "hourly_loss_usd": 1500.0,
         "contains_pci": 0, "contains_pii": 0, "regulatory_fine_risk": 0,
         "region": "apac", "data_classification": "INTERNAL",
         "owner_email": "devops@tripbiz.com"},
        {"system_id": "SYS-010", "system_name": "Email-Marketing-Service",
         "business_unit": "marketing", "hourly_loss_usd": 3200.0,
         "contains_pci": 0, "contains_pii": 1, "regulatory_fine_risk": 0,
         "region": "us", "data_classification": "CONFIDENTIAL",
         "owner_email": "crm-arch@tripbiz.com"},
    ]
    out = []
    for p in profiles:
        tier = determine_tier(p["hourly_loss_usd"], bool(p["contains_pci"]), bool(p["regulatory_fine_risk"]))
        out.append({
            **p,
            "tier": tier,
            "target_rto_hours": rto_for_tier(tier),
            "target_rpo_hours": rpo_for_tier(tier),
        })
    return out


def seed_systems(verbose=False):
    conn = get_conn()
    # 先清空
    conn.execute("DELETE FROM systems")
    for s in _make_systems():
        conn.execute(
            """INSERT INTO systems
               (system_id, system_name, business_unit, hourly_loss_usd,
                contains_pci, contains_pii, regulatory_fine_risk,
                tier, target_rto_hours, target_rpo_hours,
                region, data_classification, owner_email)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (s["system_id"], s["system_name"], s["business_unit"], s["hourly_loss_usd"],
             s["contains_pci"], s["contains_pii"], s["regulatory_fine_risk"],
             s["tier"], s["target_rto_hours"], s["target_rpo_hours"],
             s["region"], s["data_classification"], s["owner_email"])
        )
    conn.commit()
    if verbose:
        print(f"[+] Seeded {len(_make_systems())} systems")
    return len(_make_systems())


# ============================================
# 1 demo exercise + 4 phase responses + 5 CAPs
# ============================================
def seed_initial_exercise(verbose=False):
    conn = get_conn()
    conn.execute("DELETE FROM responses")
    conn.execute("DELETE FROM caps")
    conn.execute("DELETE FROM exercises")

    today = datetime.now(timezone.utc)
    exercise_id = "EX-" + today.strftime("%Y%m%d") + "-001"
    started_at = today - timedelta(hours=4)
    finished_at = today

    participants = ["SOC Analyst", "IT Infrastructure Lead", "Incident Response Lead",
                    "Cloud Ops", "Head of IT GRC", "Legal Counsel", "CISO",
                    "PR / Communications", "DPO", "DR Coordinator", "Application Engineering"]

    conn.execute(
        """INSERT INTO exercises
           (exercise_id, scenario_type, scenario_title, started_at, finished_at,
            facilitator, participants, status, overall_score, rto_actual_hours, rpo_actual_hours)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (exercise_id, "ransomware_global", "跨国勒索软件爆发桌面演练",
         started_at.isoformat(), finished_at.isoformat(),
         "resilience-lead", json.dumps(participants, ensure_ascii=False),
         "COMPLETED", 0.0, 3.5, 0.5)
    )

    # 4 个 phase 的演示响应（混合好/坏决策，演示评分）
    demo_responses = [
        # Phase 1: 部分正确 + 偏慢
        {"inject_id": 1, "phase_title": TABLETOP_INJECTS[0]["phase_title"],
         "stakeholder": "SOC Analyst",
         "decision_taken": "Isolate workstation via EDR network containment; escalate to SEV-1 within 20 min.",
         "decision_correct": 1, "time_to_decide_min": 12},
        {"inject_id": 1, "phase_title": TABLETOP_INJECTS[0]["phase_title"],
         "stakeholder": "IT Infrastructure Lead",
         "decision_taken": "Disable VPN gateway globally pending forensic review.",
         "decision_correct": 1, "time_to_decide_min": 18},
        # Phase 2: 部分 OK，缺 immutable backup
        {"inject_id": 2, "phase_title": TABLETOP_INJECTS[1]["phase_title"],
         "stakeholder": "Incident Response Lead",
         "decision_taken": "Activate IR war room; declare DR event for Tier-0 systems.",
         "decision_correct": 1, "time_to_decide_min": 25},
        {"inject_id": 2, "phase_title": TABLETOP_INJECTS[1]["phase_title"],
         "stakeholder": "Cloud Ops",
         "decision_taken": "Attempt to restore from snapshots — fails, snapshots deleted.",
         "decision_correct": 0, "time_to_decide_min": 35},
        # Phase 3: 监管通报做对
        {"inject_id": 3, "phase_title": TABLETOP_INJECTS[2]["phase_title"],
         "stakeholder": "Legal Counsel",
         "decision_taken": "Engage OFAC counsel; do not negotiate ransom; coordinate GDPR 72h notification to DPA.",
         "decision_correct": 1, "time_to_decide_min": 45},
        {"inject_id": 3, "phase_title": TABLETOP_INJECTS[2]["phase_title"],
         "stakeholder": "DPO",
         "decision_taken": "Trigger PIPL immediate notice template to CAC; coordinate with EMEA DPA within 72h.",
         "decision_correct": 1, "time_to_decide_min": 50},
        # Phase 4: 净室恢复做对，但缺 web shell scan
        {"inject_id": 4, "phase_title": TABLETOP_INJECTS[3]["phase_title"],
         "stakeholder": "DR Coordinator",
         "decision_taken": "Initiate clean room recovery in isolated AWS account using immutable cold storage.",
         "decision_correct": 1, "time_to_decide_min": 60},
        {"inject_id": 4, "phase_title": TABLETOP_INJECTS[3]["phase_title"],
         "stakeholder": "Application Engineering",
         "decision_taken": "Restore booking API read-only; backlog queued; malware scan skipped due to time pressure.",
         "decision_correct": 0, "time_to_decide_min": 75},
    ]

    total_score = 0.0
    for r in demo_responses:
        sc = score_response(r["inject_id"], r["decision_taken"], r["time_to_decide_min"], r["decision_correct"])
        total_score += sc["score"]
        conn.execute(
            """INSERT INTO responses
               (exercise_id, inject_id, phase_title, stakeholder, decision_taken,
                decision_correct, score, time_to_decide_min, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (exercise_id, r["inject_id"], r["phase_title"], r["stakeholder"],
             r["decision_taken"], r["decision_correct"], sc["score"],
             r["time_to_decide_min"],
             json.dumps({"breakdown": {"correctness": sc["correctness_pts"],
                                       "speed": sc["speed_pts"],
                                       "quality": sc["quality_pts"]}}, ensure_ascii=False))
        )

    overall = round((total_score / max(1, len(demo_responses))) * 4, 2)  # 8 个响应 → 总分 100
    conn.execute(
        "UPDATE exercises SET overall_score=? WHERE exercise_id=?",
        (overall, exercise_id)
    )

    # 5 mock CAPs
    demo_caps = [
        {"finding": "No immutable (WORM/Air-Gapped) backups in secondary region; "
                    "primary snapshots in same AWS account were deleted.",
         "severity": "CRITICAL",
         "owner": "Cloud Ops",
         "owner_email": "cloud-ops@tripbiz.com",
         "action_plan": "Deploy AWS S3 Object Lock in Compliance Mode; cross-account copy to isolated backup account.",
         "due_date": (today + timedelta(days=30)).strftime("%Y-%m-%d"),
         "framework_ref": "ISO 27001 A.5.29 / SOC 2 A1.2"},
        {"finding": "Out-of-band communication channel (Signal / Wire / phone tree) not tested.",
         "severity": "HIGH",
         "owner": "Head of IT GRC",
         "owner_email": "grc-head@tripbiz.com",
         "action_plan": "Quarterly OOB drill across APAC/EMEA/US; publish runbook v2.",
         "due_date": (today + timedelta(days=21)).strftime("%Y-%m-%d"),
         "framework_ref": "ISO 27001 A.5.29"},
        {"finding": "No on-call DPO contact in EU/UK for 72-hour GDPR notification window.",
         "severity": "CRITICAL",
         "owner": "Legal Counsel",
         "owner_email": "legal@tripbiz.com",
         "action_plan": "Contract external DPO service; update incident runbook with primary + backup contacts.",
         "due_date": (today + timedelta(days=14)).strftime("%Y-%m-%d"),
         "framework_ref": "GDPR Art.33 / PIPL Art.57"},
        {"finding": "Malware persistence scan skipped in Phase 4 — risk of restoring web shells.",
         "severity": "HIGH",
         "owner": "Application Engineering",
         "owner_email": "app-eng@tripbiz.com",
         "action_plan": "Mandatory pre-promotion EDR + static malware scan in clean room recovery checklist.",
         "due_date": (today + timedelta(days=45)).strftime("%Y-%m-%d"),
         "framework_ref": "SOC 2 A1.3"},
        {"finding": "Backup restoration drill documentation outdated; missing recenter system list.",
         "severity": "MEDIUM",
         "owner": "DR Coordinator",
         "owner_email": "dr-coord@tripbiz.com",
         "action_plan": "Quarterly DR runbook review; align with latest systems inventory.",
         "due_date": (today + timedelta(days=60)).strftime("%Y-%m-%d"),
         "framework_ref": "SOC 2 A1.2"},
    ]
    for i, c in enumerate(demo_caps, 1):
        cap_id = f"CAP-{i:03d}"
        sev = cap_severity(c["finding"])  # 用引擎验证关键词
        sev = sev if sev in ("CRITICAL", "HIGH", "MEDIUM") else c["severity"]
        conn.execute(
            """INSERT INTO caps
               (cap_id, exercise_id, inject_id, finding, severity,
                owner, owner_email, action_plan, due_date, status, framework_ref)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (cap_id, exercise_id, 2 if "backup" in c["finding"].lower() else None,
             c["finding"], sev, c["owner"], c["owner_email"],
             c["action_plan"], c["due_date"], "OPEN", c["framework_ref"])
        )

    conn.commit()
    if verbose:
        print(f"[+] Seeded exercise {exercise_id} (overall_score={overall})")
    return {"exercise_id": exercise_id, "overall_score": overall,
            "responses": len(demo_responses), "caps": len(demo_caps)}


def seed_all(verbose=False):
    init_db(verbose=verbose)
    n = seed_systems(verbose=verbose)
    e = seed_initial_exercise(verbose=verbose)
    return {"systems": n, "exercise": e}


if __name__ == "__main__":
    print(seed_all(verbose=True))