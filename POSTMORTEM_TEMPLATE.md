# Post-Mortem Report

> **Blameless post-mortems focus on systemic causes, not individual blame.**
> The goal is to learn and improve, not to assign fault.

---

## Incident Summary

| Field | Details |
|-------|---------|
| **Incident ID** | INC-YYYY-MM-DD-001 |
| **Date** | YYYY-MM-DD |
| **Duration** | X hours Y minutes |
| **Severity** | P1 / P2 / P3 |
| **Affected Service** | |
| **Affected Resource** | |
| **Incident Commander** | |
| **Status** | Resolved / Ongoing |

---

## Impact

**User Impact:**
_Describe what users experienced. Be specific — how many users, what functionality was affected, what error messages they saw._

**Business Impact:**
_Describe business impact — revenue, SLA breach, customer escalations, data loss._

**SLO Impact:**
_Which SLOs were breached? By how much? What is the remaining error budget?_

---

## Timeline

All times in UTC.

| Time | Event |
|------|-------|
| HH:MM | Alert fired — describe the alert |
| HH:MM | On-call engineer acknowledged incident |
| HH:MM | Initial investigation began |
| HH:MM | Root cause identified |
| HH:MM | Mitigation applied |
| HH:MM | Service restored |
| HH:MM | Incident closed |

---

## Root Cause Analysis

### What happened?
_A clear, factual description of the root cause. No blame, no "human error" — describe the system condition that allowed this to happen._

### Five Whys

| Why | Answer |
|-----|--------|
| Why did the incident occur? | |
| Why did that happen? | |
| Why did that happen? | |
| Why did that happen? | |
| Why did that happen? | |

**Root cause:** _The systemic issue at the bottom of the Five Whys chain._

### Contributing Factors
_List other factors that contributed to the incident or made it worse._

- 
- 
- 

---

## Detection

**How was the incident detected?**
- [ ] Azure Monitor alert fired automatically
- [ ] Customer report
- [ ] Internal team member noticed
- [ ] Third-party monitoring
- [ ] Other: ___

**Time to detection:** _How long from incident start to alert firing?_

**Was detection fast enough?** _If not, what alerting gaps exist?_

---

## Response

**How was the incident resolved?**
_Describe the mitigation steps taken. What worked, what didn't._

**Auto-remediation:**
- [ ] Restart App button used via incident-bot
- [ ] Scale Out button used via incident-bot
- [ ] Manual intervention required
- [ ] No remediation needed

**Was the runbook helpful?**
- [ ] Yes — followed as written
- [ ] Partially — needed additional steps
- [ ] No — runbook was inaccurate or missing
- [ ] No runbook existed

**Runbook feedback:**
_If the AI-generated runbook was missing steps or inaccurate, note what should be added._

---

## What Went Well

_List things that worked well during the incident response. Celebrate these._

-
-
-

---

## What Went Wrong

_List things that didn't work well. Be specific and systemic — avoid "person X made a mistake."_

-
-
-

---

## Action Items

| Action | Owner | Due Date | Priority |
|--------|-------|----------|----------|
| | | | P1/P2/P3 |
| | | | P1/P2/P3 |
| | | | P1/P2/P3 |

---

## Lessons Learned

_What does the team now know that it didn't know before? What would you do differently?_

-
-
-

---

## Metrics

| Metric | Value |
|--------|-------|
| Time to Detection (TTD) | |
| Time to Acknowledge (TTA) | |
| Time to Mitigate (TTM) | |
| Time to Resolve (TTR) | |
| Total Downtime | |
| Users Affected | |
| Error Budget Consumed | |

---

## Follow-up

- [ ] Action items tracked in issue tracker
- [ ] Runbook updated based on findings
- [ ] Alert thresholds reviewed
- [ ] Post-mortem shared with team
- [ ] SLO/SLA report updated

---

*Post-mortem completed by:*
*Date completed:*
*Reviewed by:*