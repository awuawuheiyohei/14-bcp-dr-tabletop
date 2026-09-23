# 14. 业务连续性与灾难恢复（BCP/DR）计划与网络安全桌面演练管理

## 1. 项目背景与对齐 JD 核心点

### 1.1 岗位诉求对齐
* **Senior Cyber Security Analyst (岗位 A)**：
  - **核心职能**：主导安全事件根因分析（RCA）、威胁遏制（Containment）、根除（Eradication）与恢复（Recovery）。
  - **跨团队全球协同**：在发生重大突发事件时，联动全球 SOC、IT 基础架构运维与法务（Legal）团队协同响应并满足监管通报时效。
* **Senior IT GRC Specialist (岗位 B)**：
  - **全球业务连续性与审计对齐**：对接 ISO 27001:2022（A.5.29 中断期间的信息安全、A.5.30 ICT 业务连续性准备）、SOC 2（Availability 信任原则 A1.2 容灾备份与定期恢复测试、A1.3 恢复目标验证）。
  - **对客与商业尽调（Client RFP / Due Diligence）**：跨国企业客户在企业差旅/SaaS采购时，要求出示完整的 BCP 计划、真实恢复演练报告及第三方审计证明。
  - **跨区域协同**：协调亚太（新加坡、日本、中国）等多地利益相关者开展联合演练与应急推演。

### 1.2 业务痛点与项目定位
很多跨国企业的业务连续性管理（BCM）存在严重的“纸面合规”弊端：
1. **BIA（业务影响分析）脱离实际**：各业务线主管凭主观感觉填写，导致所有系统都自称“RTO < 1小时”，IT 灾备架构资源浪费或无法兑现承诺。
2. **缺乏网络安全维度的 DR 演练**：传统的容灾演练仅测试机房断电或数据库主从切换；一旦遭遇现代勒索软件攻击（Ransomware），生产环境与只读备份可能同时被加密，原有灾备方案瞬间失效。
3. **法律与合规时效失守**：根据中国《个人信息保护法》(PIPL) 与欧盟 GDPR，重大数据泄露必须在法定时间内（如 GDPR 72小时内）向监管机构通报，跨国团队往往因责任不清导致监管重罚。
4. **演练无闭环（Lessons Learned 悬空）**：演练结束后仅写一篇形式主义通报，发现的权限单点、备份验证失败等根本缺陷无人整改。

本项目构建一个**实战化、数字化的 BCP/DR 与网络安全桌面演练（Tabletop Exercise, TTX）管理系统**：集成 BIA 影响分析与 RTO/RPO 动态定级、内置真实的全球跨国勒索软件攻击桌面推演剧本（4 个阶段事件注入）、提供多部门量化评估问卷与整改纠正行动项（Corrective Action Plan, CAP）追踪看板。

---

## 2. Mac 本地运行环境架构与依赖

### 2.1 技术栈选型
* **开发语言**：Python 3.10+
* **用户交互与推演演练看板**：Streamlit（构建分阶段的情景注入与互动式演练大屏）
* **底层数据格式**：SQLite / JSON（持久化 BIA 系统档案、演练打分与 CAP 整改项）
* **文档生成**：内置 Markdown 报告导出引擎（一键生成符合 ISO 27001 / SOC 2 审计标准的演练复盘报告）

### 2.2 本地运行架构图
```
      [Business Impact Analysis (BIA) Module]
        ├── 财务损失评估 (Financial Loss per Hour)
        ├── 客户履约违约风险 (SLA Penalty)
        └── 确定服务级别划分 (Tier 0 / Tier 1 / Tier 2) -> RTO / RPO
                       │
                       ▼
      [Cybersecurity Tabletop Exercise (TTX) Simulator]
        ├── Phase 1: 早期告警与可疑外联 (Hour 0 - EDR/SOC)
        ├── Phase 2: 横向移动与域控/核心数据库沦陷 (Hour 4 - IT/Sec)
        ├── Phase 3: 勒索勒索信出现与监管合规倒计时 (Hour 12 - Legal/PR/C-Suite)
        └── Phase 4: 备份清洗恢复与生产业务切流 (Hour 24 - Disaster Recovery)
                       │
                       ▼
         [Post-Exercise Evaluation & CAP Board]
           ├── 各部门反应敏捷度量化评分
           ├── 纠偏行动计划（CAP）跟踪
           └── 一键导出 SOC 2 / ISO 27001 审计准备包
```

### 2.3 依赖安装清单 (`requirements.txt`)
```txt
streamlit>=1.30.0
pydantic>=2.5.0
pandas>=2.1.0
pytest>=7.4.0
```

---

## 3. Vibe Coding Prompt（可直接复制给 Cursor / Claude Code）

```markdown
Role: Lead Resilience Engineer & GRC Director
Task: 编写一个支持 BIA（业务影响分析）评估与网络安全桌面演练（Tabletop Exercise）的本地运行管理系统。

功能需求：
1. `bia_calculator.py`：
   - 输入业务系统参数：系统名称、业务部门、每小时停机预估财务损失 ($/hr)、是否有持卡人数据 (PCI) 或个人信息 (PII)、合规违约风险。
   - 算法计算系统关键等级：
     * Tier 0 (Mission Critical): 停机损失 > $50,000/hr 或涉核心支付，RTO <= 2h, RPO = 0 (实时同步)；
     * Tier 1 (Business Critical): 停机损失 $10,000-$50,000/hr，RTO <= 8h, RPO <= 1h；
     * Tier 2 (Internal Support): RTO <= 24h, RPO <= 12h。
2. `tabletop_scenario.py`：
   - 内置“跨国出海平台全球勒索软件爆发”4阶段推演脚本：
     - Inject 1: 亚太海外分支机构终端触发 CrowdStrike EDR 报警，检测到疑似 Mimikatz 凭据抓取；
     - Inject 2: 攻击者利用特权账户横向移动至云核心数据库，加密生产订单系统，灾备中心收到数据篡改异常；
     - Inject 3: 黑客发布勒索信要求 500 万美元门罗币，涉及 20 万跨国客户 PII 数据外泄风险，触发 GDPR/PIPL 72小时报备倒计时；
     - Inject 4: 执行不可变灾备（Air-Gapped Immutable Backup）恢复，隔离受感染网络，验证 RTO/RPO 达成率。
   - 每个阶段包含：情景通报、分发给 SOC/IT/Legal/PR 的决策选择题、专业参考指引。
3. `cap_tracker.py` (Corrective Action Plan 纠偏行动项管理)：
   - 记录演练中暴露的缺陷（如：“离线备份缺少测试凭证”、“法务未在通讯录中列明监管第一联系人”）；
   - 跟踪责任人、整改措施、复测期限与完成状态。
4. `app.py`：Streamlit Web 界面：
   - 模块 1：BIA 评估问卷与关键资产 RTO/RPO 矩阵；
   - 模块 2：交互式桌面演练推演工作台（带倒计时与决策树）；
   - 模块 3：演练成果与整改项看板，一键导出用于客户 RFP 及外部审计的《BCP/DR 演练总结报告》。
```

---

## 4. 核心代码与系统实现

### 4.1 业务影响分析（BIA）与 RTO/RPO 定级计算器 (`bia_calculator.py`)

```python
from enum import Enum
from pydantic import BaseModel, Field

class CriticalityTier(str, Enum):
    TIER_0_MISSION_CRITICAL = "Tier-0: Mission Critical"
    TIER_1_BUSINESS_CRITICAL = "Tier-1: Business Critical"
    TIER_2_OPERATIONAL = "Tier-2: Operational Support"

class SystemBIAProfile(BaseModel):
    system_name: str
    business_unit: str
    hourly_financial_loss_usd: float = Field(ge=0)
    contains_pci_cde_data: bool = False
    contains_global_pii: bool = False
    regulatory_fine_risk: bool = False

    @property
    def determined_tier(self) -> CriticalityTier:
        if self.hourly_financial_loss_usd >= 50000 or self.contains_pci_cde_data:
            return CriticalityTier.TIER_0_MISSION_CRITICAL
        elif self.hourly_financial_loss_usd >= 10000 or self.regulatory_fine_risk:
            return CriticalityTier.TIER_1_BUSINESS_CRITICAL
        return CriticalityTier.TIER_2_OPERATIONAL

    @property
    def target_rto_hours(self) -> int:
        """Recovery Time Objective (最大可容忍停机时间)"""
        tier = self.determined_tier
        if tier == CriticalityTier.TIER_0_MISSION_CRITICAL:
            return 2
        elif tier == CriticalityTier.TIER_1_BUSINESS_CRITICAL:
            return 8
        return 24

    @property
    def target_rpo_hours(self) -> float:
        """Recovery Point Objective (最大可容忍数据丢失时间)"""
        tier = self.determined_tier
        if tier == CriticalityTier.TIER_0_MISSION_CRITICAL:
            return 0.0 # 实时同步/秒级
        elif tier == CriticalityTier.TIER_1_BUSINESS_CRITICAL:
            return 1.0 # 最多 1 小时
        return 12.0
```

### 4.2 勒索攻击桌面演练情景与注入数据 (`tabletop_scenario.py`)

```python
from typing import List, Dict
from pydantic import BaseModel

class TabletopInject(BaseModel):
    inject_id: int
    phase_title: str
    timeline: str
    scenario_description: str
    key_stakeholders: List[str]
    discussion_questions: List[str]
    regulatory_considerations: str

TABLETOP_SCENARIO_INJECTS = [
    TabletopInject(
        inject_id=1,
        phase_title="Phase 1: Initial Detection & Infiltration",
        timeline="T + 00:00 (Friday 22:30 SGT)",
        scenario_description="CrowdStrike EDR triggers high-priority alerts on an overseas customer support workstation in Singapore. Detected suspicious PowerShell execution and LSASS memory dumping. Shortly after, multiple failed RDP connections observed across the corporate VPN gateway.",
        key_stakeholders=["SOC Analyst", "IT Infrastructure Lead"],
        discussion_questions=[
            "Who has the authority to isolate the compromised workstation network-wide at 22:30?",
            "What criteria determine if this alert escalates to an official Security Incident (SEV-1)?",
            "Are on-call rosters and contact lists updated across APAC, US, and EMEA regions?"
        ],
        regulatory_considerations="Internal containment only; determine potential scope of breach."
    ),
    TabletopInject(
        inject_id=2,
        phase_title="Phase 2: Lateral Movement & Ransomware Deployment",
        timeline="T + 04:30 (Saturday 03:00 SGT)",
        scenario_description="Attackers leveraged compromised Domain Admin credentials to disable central AV updates and deployed BlackCat/ALPHV ransomware. The primary booking database and customer-facing portal are encrypted. Storage snapshots in the same AWS account were deleted.",
        key_stakeholders=["Incident Response Lead", "Cloud Ops", "Head of IT GRC", "Head of Business Unit"],
        discussion_questions=[
            "Do we have isolated, immutable (WORM/Air-Gapped) backups in a secondary clean cloud region?",
            "At what point is the decision made to declare a formal Disaster Recovery (DR) event?",
            "How do we establish out-of-band communication if corporate Slack and Google Workspace credentials might be compromised?"
        ],
        regulatory_considerations="Assess potential RTO/RPO breach for Tier-0 core systems."
    ),
    TabletopInject(
        inject_id=3,
        phase_title="Phase 3: Extortion Demand & Regulatory Breach Notification",
        timeline="T + 12:00 (Saturday 10:30 SGT)",
        scenario_description="Ransom note demands $5M in Monero. The threat actor publishes proof of acquiring 200,000 international customer passports and credit card tokens on a dark web leak site. Media starts asking questions.",
        key_stakeholders=["Legal Counsel", "CISO", "PR / Communications", "DPO (Data Protection Officer)"],
        discussion_questions=[
            "What is the corporate policy regarding ransomware payment negotiation (OFAC sanctions risk)?",
            "What are the mandatory regulatory notification deadlines under China PIPL (immediate), GDPR (72 hours), and Singapore PDPA (3 days)?",
            "How should external communications and customer advisory notices be coordinated?"
        ],
        regulatory_considerations="Mandatory data breach notification clock is actively ticking."
    ),
    TabletopInject(
        inject_id=4,
        phase_title="Phase 4: Clean Room Recovery & BCP Continuity Verification",
        timeline="T + 28:00 (Sunday 02:30 SGT)",
        scenario_description="DR team initiates recovery into a clean-room AWS environment using immutable cold-storage backups. Database integrity verified. Core booking API restored with read-only state, processing backlog queued.",
        key_stakeholders=["DR Coordinator", "Application Engineering", "Head of IT GRC"],
        discussion_questions=[
            "Did actual recovery time meet the 8-hour RTO target for Tier-1 booking systems?",
            "How do we ensure malware persistence (such as dormant web shells) is not restored from backup images?",
            "What lessons learned (CAP) need to be logged into the GRC Risk Register?"
        ],
        regulatory_considerations="SOC 2 A1.2 compliance evidence generation; post-incident forensic report."
    )
]
```

---

## 5. 测试验证与自动化测试脚本

创建自动化测试脚本 `test_bcp_framework.py`：

```python
from bia_calculator import SystemBIAProfile, CriticalityTier
from tabletop_scenario import TABLETOP_SCENARIO_INJECTS

def test_bia_tiering_logic():
    # 场景 1: 核心支付交易网关 (带 PCI CDE 数据)
    payment_gw = SystemBIAProfile(
        system_name="TripBiz-Payment-Gateway",
        business_unit="FinTech / Payments",
        hourly_financial_loss_usd=80000.0,
        contains_pci_cde_data=True,
        contains_global_pii=True
    )
    assert payment_gw.determined_tier == CriticalityTier.TIER_0_MISSION_CRITICAL
    assert payment_gw.target_rto_hours == 2
    assert payment_gw.target_rpo_hours == 0.0

    # 场景 2: 内部运营分析系统
    internal_bi = SystemBIAProfile(
        system_name="BI-Reporting-DWH",
        business_unit="Marketing",
        hourly_financial_loss_usd=2000.0,
        contains_pci_cde_data=False,
        contains_global_pii=False
    )
    assert internal_bi.determined_tier == CriticalityTier.TIER_2_OPERATIONAL
    assert internal_bi.target_rto_hours == 24
    assert internal_bi.target_rpo_hours == 12.0

def test_tabletop_scenario_completeness():
    assert len(TABLETOP_SCENARIO_INJECTS) == 4
    # 验证关键监管要素覆盖
    all_regs = " ".join([inj.regulatory_considerations for inj in TABLETOP_SCENARIO_INJECTS])
    assert "PIPL" in all_regs or "GDPR" in all_regs
    assert "SOC 2" in all_regs

if __name__ == "__main__":
    test_bia_tiering_logic()
    test_tabletop_scenario_completeness()
    print("All BCP/DR and Tabletop Exercise tests passed successfully!")
```

---

## 6. 简历包装（STAR 法则）

### 中文版
* **情境（Situation）**：企业全球化业务扩张中，原有容灾预案（BCP/DR）多年未更新且停留在纸面，各系统 RTO/RPO 目标虚标严重，无法满足跨国高价值 B2B 客户的安全 RFP 审查要求，且在 SOC 2（Availability A1.2）与 ISO 27001 审计中面临有效性质疑。
* **任务（Task）**：统筹建立覆盖亚太与欧美分支的现代化业务连续性（BCP/DR）与网络安全韧性体系，重构量化 BIA 模型，并主导端到端的实战化网络攻防桌面演练。
* **行动（Action）**：
  - 重新设计多维度 BIA 分析矩阵，通过财务损失、客户违约与合规罚款将全公司 45+ 核心业务系统划分为 Tier 0~2，科学制定可落地的 RTO/RPO 恢复目标。
  - 策划并主导了一场全跨国模拟“勒索软件加密生产数据库并敲诈”的实操桌面演练（TTX），协同 SecOps、IT 运维、法务、公关与海外管理层推演 4 阶段应急响应。
  - 演练后沉淀《纠偏行动计划（CAP）》，推动落地离线不可变冷备份（Air-Gapped S3 Object Lock）与跨国数据合规 72 小时监管通报 SOP。
* **结果（Result）**：核心业务系统实际恢复耗时从不可知优化为验证达标的 RTO < 4 小时；演练报告与 BCP 底稿成功赋能销售团队完成 5 家国际头部企业的高标准安全尽调（RFP），顺利通过 SOC 2 Availability 原则审计。

### English Version
* **Situation**: The company's legacy BCP/DR plans were outdated and theoretical, with unrealistic RTO/RPO targets that undermined client confidence during enterprise RFP due diligence and raised audit flags under SOC 2 Availability criteria (A1.2/A1.3).
* **Task**: Spearheaded an enterprise-wide Business Continuity and Cyber Resilience overhaul, establishing a data-driven BIA model and executing realistic cross-functional tabletop exercises.
* **Action**:
  - Re-architected the Business Impact Analysis (BIA) framework across 45+ services, categorizing systems into Tier 0-2 based on financial and regulatory loss to establish realistic RTO/RPO baselines.
  - Designed and facilitated an executive-level Tabletop Exercise simulating a global ransomware attack, leading SOC, IT, Legal, and PR through 4 incident injects including extortion and GDPR/PIPL regulatory notifications.
  - Formulated a post-exercise Corrective Action Plan (CAP) that enforced AWS immutable backups (S3 Object Lock) and established standardized cross-border breach notification playbooks.
* **Result**: Validated a verified <4-hour RTO for Tier-0 services, eliminated single points of failure in backup restoration, and produced defensible BCP/DR documentation that accelerated deal closures with 5 major enterprise clients.

---

## 7. 面试高频追问及优秀应答策略

### Q1：在开展 BIA（业务影响分析）时，每个业务线负责人都坚称自己的系统是“Tier-0、一分钟都不能停”，导致 IT 容灾成本失控，你如何解决这种博弈？
* **应答策略**：
  - **转换话语体系：用“量化财务与法律代价”代替“主观意愿”**：
    “不能单凭业务主管的口头诉求，而是通过明确的客观量化公式：系统每停机 1 小时造成的直接订单损失是多少？因客户履约违约造成的合同罚款是多少？是否违反如支付牌照、PCI DSS 或个人隐私强制法规？”
  - **展示架构与成本对价**：向业务负责人展示 SLA 等级与架构成本对应关系：“实现 RTO < 15 分钟需要双活多活跨区集群，成本是普通冷备的 5 倍以上，这笔预算需要从该业务线的年度 P&L 中扣除。”在成本倒逼下，业务方往往会理性回归至真实的业务容忍限度。
  - **高管仲裁与签批（Executive Sign-off）**：最终将分级矩阵提交给 COO、CTO 与 Head of GRC 联合评审，形成企业级基准，防止部门主义。

### Q2：面对勒索软件攻击（Ransomware），传统异地灾备数据库复制常常也会被同步“污染”或加密，你们如何设计真正的抗勒索恢复架构？
* **应答策略**：
  - **逻辑隔离与不可变存储（Immutability & Air-Gap）**：
    1. **S3 Object Lock (WORM - Write Once, Read Many)**：在合规模式（Compliance Mode）下，哪怕拥有 Root 账号在保留期内也无法删除或覆盖备份数据；
    2. **跨账号隔离（Dedicated Backup Account）**：备份数据通过 AWS Backup 自动复制到完全独立的受限云账户中，生产环境的 IAM 凭据对备份账户完全不可见且无权修改；
    3. **净室恢复（Clean Room Environment）**：灾备恢复不是原地回滚，而是准备一个网络完全隔离的洁净环境，在将备份导入前先由 EDR 与取证团队执行恶意代码静态签名与后门扫描，确认洁净后方可逐步恢复对外生产流量。

### Q3：出海业务（如 Trip.Biz 面向日本、新加坡、欧洲与中国）遭遇重大安全事件时，如何满足不同法域的“数据泄露通报（Breach Notification）”时限？
* **应答策略**：
  - **建立统一的全局通报矩阵与多时区触发机制**：
    1. **不同法规时效梳理**：
       - **中国 PIPL**：发生或可能发生个人信息泄露，应当“立即”采取补救措施并通知履行个人信息保护职责的部门；
       - **欧盟 GDPR**：控制者在知晓泄露后，应在“72 小时内”通报主管监管机构（DPA）；若对个人权益产生高风险，应“无不当延误”通知数据主体；
       - **新加坡 PDPA**：对受影响超过 500 人或造成重大伤害的泄露，应在“3 个自然日内”通报 PDPC。
    2. **演练与机制落地**：在桌面演练中，法务与数据保护官（DPO）必须在 T+2 小时内介入判定是否构成“可确认的个人数据泄露”，并启动标准通报模板草案；内部通讯绝不在未经加密的常规邮件中提及敏感未核实细节，确保跨国公关、法务与监管对接步调高度一致。
