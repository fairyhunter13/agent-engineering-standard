---
name: runbooks-and-incident-response
description: Write actionable runbooks for on-call and establish an incident response process that reduces MTTR and preserves institutional knowledge.
discipline: infra
tags: [sre, incident-response, runbooks, on-call, mttr]
---

# Runbooks and Incident Response

## When to use

On-call engineers spend more than 20 minutes diagnosing known, recurring issues. Every incident is
treated as novel because knowledge lives in a single engineer's head. Post-mortems are skipped
because there is no incident response process. The same alert fires monthly with no documented
resolution path.

## Signal

- MTTR >1 hour for incidents that the team has seen before — time is spent re-diagnosing from
  scratch rather than executing a known playbook.
- No runbook link in the alert annotation — engineers start every incident from `kubectl get pods`.
- Knowledge about how to resolve a specific alert is siloed in one or two engineers who are the
  de-facto on-call.
- The same incident recurs monthly (same service, same root cause) with no permanent fix and no
  runbook.
- Handoff between on-call shifts is verbal — no written incident summary or current status.
- Alert fires, gets acknowledged, and is closed without any record of what was done.

## Why

Without runbooks, every responder re-diagnoses every incident from scratch. MTTR is bounded below
by the time it takes an unfamiliar engineer to understand the system, find the relevant metrics,
and determine the correct action. For known failure modes, this is unnecessary rework that increases
user impact duration.

Documented incident response also enables junior engineers to handle incidents confidently and
reduces the bus-factor of on-call capability.

## Remediate

1. **Write a runbook for every alert.** Each runbook should answer:
   - **What is this alert?** One sentence describing what triggered.
   - **Symptoms**: what the user experiences.
   - **Diagnostic commands**: exact commands to run to understand the scope.
     ```bash
     kubectl get pods -n production -l app=payments
     kubectl logs -n production deployment/payments --since=15m | grep ERROR
     kubectl top pods -n production -l app=payments
     ```
   - **Resolution steps**: numbered, concrete steps to resolve the most common cause.
   - **Escalation path**: who to page if the steps don't resolve it.
   - **Recovery verification**: how to confirm the issue is resolved.

2. **Link the runbook URL in every alert annotation.** Add a `runbook_url` label to Prometheus
   alerting rules or equivalent:
   ```yaml
   - alert: PaymentsHighErrorRate
     expr: rate(http_requests_total{service="payments",status="5xx"}[5m]) > 0.01
     annotations:
       runbook_url: https://wiki.company.com/runbooks/payments-high-error-rate
       summary: "Payments error rate above 1%"
   ```
   When the alert fires, the on-call engineer clicks the link and follows the runbook — no searching.

3. **Keep runbooks in version control.** Runbooks drift from reality if not maintained alongside
   code changes. Store runbooks as Markdown in the service repository or a central SRE repository.
   Review and update runbooks as part of post-mortem action items.

4. **Follow a structured incident response process:**
   - **Declare**: as soon as impact is confirmed, declare the incident in your incident management
     tool (PagerDuty, Incident.io, Opsgenie). Do not wait until you understand the cause.
   - **Assign roles**: Incident Commander (IC — coordinates), Communications Lead (stakeholder
     updates), Technical Lead (diagnosis and fix).
   - **Communicate**: status update every 30 minutes to the status page and internal channels, even
     if "still investigating." Silence is worse than "no news yet."
   - **Resolve**: implement the fix; verify recovery metrics.
   - **Close**: write a brief incident summary (what happened, what was done, current status).

5. **Conduct a post-mortem within 48 hours** for all P1/P2 incidents. See `infra/blameless-postmortems`
   for the full process. At minimum, every incident close must have an action item to improve the
   runbook or prevent recurrence.

6. **Track on-call health.** Measure: pages per shift, MTTR per alert, alert volume by service.
   Alert volume >5 actionable pages per shift is unsustainable. Reduce noise through: alert
   consolidation, better thresholds, resolving toil with automation.

## References

- Google SRE Book: Chapter 14 (Managing Incidents)
- PagerDuty: Incident Response documentation
- Atlassian: Incident Management Handbook
- Site Reliability Engineering: How Google Runs Production Systems (O'Reilly)
