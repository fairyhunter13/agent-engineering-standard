---
name: blameless-postmortems
description: Conduct blameless post-mortems after incidents to systematically identify contributing factors and prevent recurrence.
discipline: infra
tags: [sre, incident-response, culture, postmortem, reliability]
---

# Blameless Post-Mortems

## When to use

After every incident with customer impact at P2 severity or above. When the same failure type
recurs — a recurring incident without a post-mortem is a missed improvement opportunity. When an
incident reveals systemic problems beyond the immediate technical cause. Whenever a team member
says "we need to make sure this never happens again."

## Signal

- Post-mortems are skipped: "we know what happened, no need to write it up."
- Root cause is consistently identified as "human error" — a sign that systemic factors are being
  missed.
- No action items are generated, or action items are generated but never tracked or closed.
- Engineers are reluctant to share full details of their actions during the incident for fear of
  blame.
- The same incident type recurs every 60–90 days — it is not being systematically prevented.
- Post-mortem documents are written but never shared — learning stays within the team.

## Why

"Human error" as a root cause is a symptom of blame-centric analysis, not a useful finding. A
human who made a mistake did so within a system that allowed the mistake to have impact. The
system — its guardrails, tooling, documentation, and processes — is what engineering teams can
change. Blaming individuals provides no systemic improvement and creates a culture of concealment
that deprives the team of the information needed to improve.

Blameless post-mortems, pioneered by Google SRE and Etsy engineering culture, treat incidents as
opportunities for system improvement. Engineers who surface the full truth of what happened (including
their own mistakes) are celebrated as contributors to organizational learning, not penalized.

## Remediate

1. **Write the post-mortem within 48 hours.** Memory fades quickly; participants are available; the
   timeline is still fresh. Use a standard template for consistency (see structure below). Assign a
   post-mortem owner (usually the IC or technical lead from the incident).

2. **Standard post-mortem template:**
   ```
   ## [Service Name] Incident Post-Mortem
   **Date**: YYYY-MM-DD
   **Severity**: P1 / P2
   **Duration**: HH:MM
   **Author(s)**: @name, @name
   **Status**: Draft / Review / Final

   ## Impact
   - Users affected: N
   - Revenue impact: $X (estimated)
   - Duration of customer-visible impact: HH:MM

   ## Timeline
   - HH:MM — [Event description]
   - HH:MM — Alert fired: [alert name]
   - HH:MM — IC declared incident
   - HH:MM — Root cause identified
   - HH:MM — Fix deployed
   - HH:MM — Incident closed

   ## Root Cause Analysis
   [What was the underlying cause? Use 5-Whys or Fishbone.]

   ## Contributing Factors
   [System factors that allowed this to happen or to have impact.]

   ## What Went Well
   [Detection, response, communication, tooling that helped.]

   ## What Could Be Improved
   [Gaps in tooling, process, monitoring, documentation.]

   ## Action Items
   | Action | Owner | Priority | Due Date | Status |
   ```

3. **Use 5-Whys to reach systemic causes, not human error.**
   Example:
   - Why did the service fail? → The DB ran out of connections.
   - Why did it run out? → Connection pool size was not configured.
   - Why wasn't it configured? → No default configuration enforced.
   - Why? → No infrastructure checklist for new service onboarding.
   - Why? → No owner for the onboarding process.
   Action: create an onboarding checklist with a designated owner.

4. **Assign action items with owners, priorities, and due dates.** Unowned action items are
   suggestions, not commitments. Every action item must have a named engineer and a realistic
   deadline. Track them in your issue tracker, not in the post-mortem document.

5. **Review open action items in the weekly SRE or engineering meeting.** Action items that are
   blocked, overdue, or deprioritized should be escalated. Without a review loop, action items age
   into abandoned intentions.

6. **Share post-mortems broadly.** Publish finalized post-mortems in a shared wiki or internal
   newsletter. Learning from incidents is more valuable than keeping them internal to the on-call
   team. Consider a monthly "incident learnings" email digest.

7. **Never include individual names in the "blame" position.** Names appear in the timeline as
   actors ("Engineer X deployed the change") — never as culprits ("Engineer X caused the outage").
   Focus on what the system allowed, not what the person did.

## References

- Google SRE Book: Chapter 15 (Postmortem Culture: Learning from Failure)
- Etsy Engineering: Blameless PostMortems and a Just Culture
- John Allspaw: "Blameless PostMortems and a Just Culture" (codeascraft.com)
- Sidney Dekker: *The Field Guide to Understanding Human Error*
