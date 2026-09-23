"""
BIA Calculator + Tabletop Scenario + CAP severity engine
依据 Security_and_GRC_14_Projects_Plan #14 PRD
"""
from enum import Enum
from typing import List


class CriticalityTier(str, Enum):
    TIER_0_MISSION_CRITICAL = "TIER_0"
    TIER_1_BUSINESS_CRITICAL = "TIER_1"
    TIER_2_OPERATIONAL = "TIER_2"


# ============================================
# BIA Tier 算法（PRD 4.1）
# ============================================
def determine_tier(hourly_loss_usd: float, contains_pci: bool, regulatory_fine_risk: bool) -> str:
    """PRD 算法：$50K/hr OR PCI → TIER_0; $10K/hr OR 监管罚款 → TIER_1; 其他 TIER_2"""
    if hourly_loss_usd >= 50000 or contains_pci:
        return CriticalityTier.TIER_0_MISSION_CRITICAL.value
    if hourly_loss_usd >= 10000 or regulatory_fine_risk:
        return CriticalityTier.TIER_1_BUSINESS_CRITICAL.value
    return CriticalityTier.TIER_2_OPERATIONAL.value


def rto_for_tier(tier: str) -> int:
    return {"TIER_0": 2, "TIER_1": 8, "TIER_2": 24}.get(tier, 24)


def rpo_for_tier(tier: str) -> float:
    return {"TIER_0": 0.0, "TIER_1": 1.0, "TIER_2": 12.0}.get(tier, 12.0)


def classify_system(profile: dict) -> dict:
    """输入系统 profile dict（含 hourly_loss_usd/contains_pci/regulatory_fine_risk），返回 tier + RTO/RPO"""
    tier = determine_tier(
        profile.get("hourly_loss_usd", 0),
        bool(profile.get("contains_pci", 0)),
        bool(profile.get("regulatory_fine_risk", 0)),
    )
    return {
        "tier": tier,
        "target_rto_hours": rto_for_tier(tier),
        "target_rpo_hours": rpo_for_tier(tier),
    }


# ============================================
# Tabletop 4 阶段剧本（PRD 4.2）
# ============================================
TABLETOP_INJECTS = [
    {
        "inject_id": 1,
        "phase_title": "Phase 1: Initial Detection & Infiltration",
        "timeline": "T + 00:00 (Friday 22:30 SGT)",
        "scenario_description": (
            "CrowdStrike EDR triggers high-priority alerts on an overseas customer support "
            "workstation in Singapore. Detected suspicious PowerShell execution and LSASS "
            "memory dumping. Multiple failed RDP connections observed across the corporate "
            "VPN gateway shortly after."
        ),
        "key_stakeholders": ["SOC Analyst", "IT Infrastructure Lead"],
        "discussion_questions": [
            "Who has the authority to isolate the compromised workstation network-wide at 22:30?",
            "What criteria determine if this alert escalates to an official Security Incident (SEV-1)?",
            "Are on-call rosters and contact lists updated across APAC, US, and EMEA regions?",
        ],
        "regulatory_considerations": "Internal containment only; determine potential scope of breach.",
        "framework_ref": "ISO 27001 A.5.24 / SOC 2 CC7.3",
    },
    {
        "inject_id": 2,
        "phase_title": "Phase 2: Lateral Movement & Ransomware Deployment",
        "timeline": "T + 04:30 (Saturday 03:00 SGT)",
        "scenario_description": (
            "Attackers leveraged compromised Domain Admin credentials to disable central AV "
            "updates and deployed BlackCat/ALPHV ransomware. The primary booking database "
            "and customer-facing portal are encrypted. Storage snapshots in the same AWS "
            "account were deleted."
        ),
        "key_stakeholders": ["Incident Response Lead", "Cloud Ops", "Head of IT GRC", "Head of Business Unit"],
        "discussion_questions": [
            "Do we have isolated, immutable (WORM/Air-Gapped) backups in a secondary clean cloud region?",
            "At what point is the decision made to declare a formal Disaster Recovery (DR) event?",
            "How do we establish out-of-band communication if corporate Slack and Google Workspace credentials might be compromised?",
        ],
        "regulatory_considerations": "Assess potential RTO/RPO breach for Tier-0 core systems.",
        "framework_ref": "ISO 27001 A.5.29 / A.5.30 / SOC 2 A1.2",
    },
    {
        "inject_id": 3,
        "phase_title": "Phase 3: Extortion Demand & Regulatory Breach Notification",
        "timeline": "T + 12:00 (Saturday 10:30 SGT)",
        "scenario_description": (
            "Ransom note demands $5M in Monero. The threat actor publishes proof of acquiring "
            "200,000 international customer passports and credit card tokens on a dark web "
            "leak site. Media starts asking questions."
        ),
        "key_stakeholders": ["Legal Counsel", "CISO", "PR / Communications", "DPO"],
        "discussion_questions": [
            "What is the corporate policy regarding ransomware payment negotiation (OFAC sanctions risk)?",
            "What are the mandatory regulatory notification deadlines under China PIPL (immediate), GDPR (72 hours), and Singapore PDPA (3 days)?",
            "How should external communications and customer advisory notices be coordinated?",
        ],
        "regulatory_considerations": "Mandatory data breach notification clock is actively ticking.",
        "framework_ref": "PIPL Art.57 / GDPR Art.33 / SOC 2 CC2.3",
    },
    {
        "inject_id": 4,
        "phase_title": "Phase 4: Clean Room Recovery & BCP Continuity Verification",
        "timeline": "T + 28:00 (Sunday 02:30 SGT)",
        "scenario_description": (
            "DR team initiates recovery into a clean-room AWS environment using immutable "
            "cold-storage backups. Database integrity verified. Core booking API restored "
            "with read-only state, processing backlog queued."
        ),
        "key_stakeholders": ["DR Coordinator", "Application Engineering", "Head of IT GRC"],
        "discussion_questions": [
            "Did actual recovery time meet the 8-hour RTO target for Tier-1 booking systems?",
            "How do we ensure malware persistence (such as dormant web shells) is not restored from backup images?",
            "What lessons learned (CAP) need to be logged into the GRC Risk Register?",
        ],
        "regulatory_considerations": "SOC 2 A1.2 compliance evidence generation; post-incident forensic report.",
        "framework_ref": "SOC 2 A1.2 / A1.3 / ISO 27001 A.5.30",
    },
]


def get_inject(inject_id: int) -> dict | None:
    for inj in TABLETOP_INJECTS:
        if inj["inject_id"] == inject_id:
            return inj
    return None


# ============================================
# 评分算法（每 phase 0-25，总分 100）
# ============================================
def score_response(inject_id: int, decision_taken: str, time_to_decide_min: int,
                   decision_correct: bool) -> dict:
    """评分 = 决策正确性(15) + 速度(<=15min 满分, 越慢越低) + 决策质量(0-10)
    返回 dict: score (0-25), breakdown dict
    """
    decision_correct = bool(decision_correct)
    # 决策正确性（15 分）
    correctness_pts = 15 if decision_correct else 0

    # 速度：≤15min 给 5 分，>120min 给 0 分（线性插值）
    if time_to_decide_min <= 15:
        speed_pts = 5
    elif time_to_decide_min >= 120:
        speed_pts = 0
    else:
        speed_pts = round(5 * (1 - (time_to_decide_min - 15) / (120 - 15)), 2)

    # 决策质量（关键词启发式 0-5）
    decision_lower = decision_taken.lower()
    quality_keywords = [
        "isolate", "contain", "immutable", "air-gap", "out-of-band",
        "law enforcement", "forensic", "ransom", "rollback", "clean room",
        "encryption", "air gapped", "immutable", "object lock",
    ]
    matches = sum(1 for k in quality_keywords if k in decision_lower)
    quality_pts = min(5, matches)

    total = correctness_pts + speed_pts + quality_pts
    return {
        "score": round(total, 2),
        "correctness_pts": correctness_pts,
        "speed_pts": speed_pts,
        "quality_pts": quality_pts,
    }


# ============================================
# CAP 严重度引擎
# ============================================
def cap_severity(finding: str) -> str:
    """根据 finding 关键词自动分级"""
    f = finding.lower()
    if any(k in f for k in ["no backup", "no immutable", "no out-of-band", "single point", "spof",
                              "no dpo", "72-hour", "72 hour"]):
        return "CRITICAL"
    if any(k in f for k in ["missing contact", "outdated", "untested", "no runbook",
                              "no monitoring"]):
        return "HIGH"
    if any(k in f for k in ["unclear", "manual", "needs review", "documentation"]):
        return "MEDIUM"
    return "LOW"


def compute_bia_portfolio_stats(systems: List[dict]) -> dict:
    """汇总 BIA 全公司画像"""
    if not systems:
        return {"total_systems": 0, "by_tier": {}, "tier_0_rto_total_hours": 0,
                "annual_dollar_at_risk": 0}
    by_tier = {"TIER_0": 0, "TIER_1": 0, "TIER_2": 0}
    hourly_loss_total = 0
    for s in systems:
        by_tier[s.get("tier", "TIER_2")] = by_tier.get(s.get("tier", "TIER_2"), 0) + 1
        hourly_loss_total += float(s.get("hourly_loss_usd", 0))
    # 假设 24h 最坏情况停机
    annual_dollar_at_risk = hourly_loss_total * 24
    return {
        "total_systems": len(systems),
        "by_tier": by_tier,
        "total_hourly_loss_usd": round(hourly_loss_total, 2),
        "worst_case_24h_loss_usd": round(annual_dollar_at_risk, 2),
    }