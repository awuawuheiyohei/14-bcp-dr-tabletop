-- BCP DR Tabletop Exercise - SQLite schema (v1.0)
-- 依据 Security_and_GRC_14_Projects_Plan #14 PRD

-- ============================================
-- BIA 系统档案
-- ============================================
CREATE TABLE IF NOT EXISTS systems (
    system_id           TEXT PRIMARY KEY,                  -- SYS-001
    system_name         TEXT NOT NULL,                     -- TripBiz-Payment-Gateway
    business_unit       TEXT NOT NULL DEFAULT 'platform',
    hourly_loss_usd     REAL NOT NULL DEFAULT 0.0,         -- $/hr
    contains_pci        INTEGER NOT NULL DEFAULT 0,        -- 0/1 PCI CDE
    contains_pii        INTEGER NOT NULL DEFAULT 0,        -- 0/1 PII
    regulatory_fine_risk INTEGER NOT NULL DEFAULT 0,       -- 0/1
    tier                TEXT NOT NULL DEFAULT 'TIER_2',     -- TIER_0 / TIER_1 / TIER_2
    target_rto_hours    INTEGER NOT NULL DEFAULT 24,
    target_rpo_hours    REAL NOT NULL DEFAULT 12.0,
    region              TEXT NOT NULL DEFAULT 'apac',
    data_classification TEXT NOT NULL DEFAULT 'INTERNAL',  -- PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED
    owner_email         TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sys_tier ON systems(tier);
CREATE INDEX IF NOT EXISTS idx_sys_unit ON systems(business_unit);

-- ============================================
-- 演练场次
-- ============================================
CREATE TABLE IF NOT EXISTS exercises (
    exercise_id     TEXT PRIMARY KEY,                       -- EX-20260924-001
    scenario_type   TEXT NOT NULL DEFAULT 'ransomware_global',
    scenario_title  TEXT NOT NULL,                          -- "跨国勒索软件爆发桌面演练"
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at     TEXT,
    facilitator     TEXT NOT NULL DEFAULT 'resilience-lead',
    participants    TEXT,                                   -- JSON list
    status          TEXT NOT NULL DEFAULT 'IN_PROGRESS',    -- IN_PROGRESS / COMPLETED / ABORTED
    overall_score   REAL NOT NULL DEFAULT 0.0,              -- 0-100
    rto_actual_hours REAL,
    rpo_actual_hours REAL
);

CREATE INDEX IF NOT EXISTS idx_ex_status ON exercises(status);

-- ============================================
-- 演练决策/响应（每 phase 一条）
-- ============================================
CREATE TABLE IF NOT EXISTS responses (
    response_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id        TEXT NOT NULL,
    inject_id          INTEGER NOT NULL,                    -- 1-4 phase
    phase_title        TEXT NOT NULL,
    stakeholder        TEXT NOT NULL,                       -- SOC / IT / Legal / PR / CISO / DPO
    decision_taken     TEXT NOT NULL,
    decision_correct   INTEGER NOT NULL DEFAULT 0,          -- 0/1
    score              INTEGER NOT NULL DEFAULT 0,           -- 0-25 per phase
    time_to_decide_min INTEGER NOT NULL DEFAULT 0,           -- 分钟
    notes              TEXT,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (exercise_id) REFERENCES exercises(exercise_id)
);

CREATE INDEX IF NOT EXISTS idx_resp_ex ON responses(exercise_id);
CREATE INDEX IF NOT EXISTS idx_resp_phase ON responses(inject_id);

-- ============================================
-- 纠偏行动项 CAP
-- ============================================
CREATE TABLE IF NOT EXISTS caps (
    cap_id           TEXT PRIMARY KEY,                       -- CAP-001
    exercise_id      TEXT NOT NULL,
    inject_id        INTEGER,                               -- 来源 phase
    finding          TEXT NOT NULL,                          -- 缺陷描述
    severity         TEXT NOT NULL DEFAULT 'MEDIUM',         -- CRITICAL / HIGH / MEDIUM / LOW
    owner            TEXT NOT NULL,                          -- 责任人
    owner_email      TEXT,
    action_plan      TEXT NOT NULL,
    due_date         TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'OPEN',           -- OPEN / IN_PROGRESS / CLOSED / VERIFIED
    closed_at        TEXT,
    verified_at      TEXT,
    framework_ref    TEXT,                                   -- ISO 27001 A.5.29 / SOC 2 A1.2 等
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (exercise_id) REFERENCES exercises(exercise_id)
);

CREATE INDEX IF NOT EXISTS idx_cap_status ON caps(status);
CREATE INDEX IF NOT EXISTS idx_cap_ex ON caps(exercise_id);

-- ============================================
-- 审计 trail
-- ============================================
CREATE TABLE IF NOT EXISTS audit_trail (
    audit_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    actor         TEXT NOT NULL,
    action        TEXT NOT NULL,
    entity_type   TEXT,
    entity_id     TEXT,
    details       TEXT,
    occurred_at   TEXT NOT NULL DEFAULT (datetime('now'))
);