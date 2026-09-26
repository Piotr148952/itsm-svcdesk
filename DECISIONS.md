---
svcdesk_decisions:
  C1: wallclock
  C2: immutable
  C3: matrix
---
<!-- ai-generated: 100% - Codex drafted the decisions and their tradeoffs from the receipted specification. -->
# Decisions

## C1 - P1 SLA runs continuously

**Decision:** Resolve R-13 versus R-14 by applying wall-clock time to both P1 targets: 15 minutes to acknowledge and four hours to resolve. Reject only the part of R-13 that pauses P1 outside office hours. P2 through P4 retain Warsaw business-hour clocks.

**Rejected alternative:** Applying business hours to every priority would allow a critical Friday-evening outage to wait until Monday before its measured allowance begins. That would satisfy R-13 but reject the around-the-clock promise in R-14.

**Reason:** P1 means organisation-wide work has stopped. Elapsed disruption matters even when the desk is closed. A paused counter would hide part of that disruption. This choice creates an operational obligation: out-of-hours coverage must be funded, or the organisation must accept recorded breaches. Software alone cannot provide a four-hour recovery capability.

**Service owner:** The Service Desk product owner, with the incident-management and on-call operations owners, must approve the coverage and cost required to support the continuous target.

**Customer outcome:** Affected users receive a deadline tied to the actual start of their outage. The organisation sees weekend failures in its breach reports; the operations team bears the staffing burden instead of removing that time from the report.

## C2 - Closed tickets remain immutable

**Decision:** Resolve R-09 versus R-10 by keeping closed tickets immutable. Reject only R-10's permission to reopen a closed ticket. Resolved tickets can still reopen through exactly seven days after resolution, as required by the remaining part of R-10 and R-11.

**Rejected alternative:** Allowing a closed ticket to reopen within seven days would reduce reporter effort but break R-09. It would change a record that the closure workflow already treats as a confirmed outcome.

**Reason:** Closure follows confirmation of the fix, while resolution is provisional. Keeping those stages distinct gives the desk a stable record of completed work. A subsequent problem uses a new ticket linked by related_to. The extra ticket can inflate ticket counts, so later analysis should distinguish linked recurrence from unrelated demand. Reopening a merely resolved ticket preserves its original deadline and therefore cannot manufacture additional SLA allowance.

**Service owner:** The Service Desk process owner owns the closure policy and its reporting implications, coordinating with the reporting owner so linked recurrence is interpreted correctly.

**Customer outcome:** Reporters can challenge an unconfirmed resolution directly within seven days. After confirmed closure they must open a linked ticket, bearing a small additional reporting burden in exchange for a stable account of the earlier outcome.

## C3 - Priority follows impact and urgency

**Decision:** Resolve R-05 versus R-06 in favour of the impact/urgency matrix. Reject R-06's VIP floor of P2. Keep reporter.vip as metadata without changing priority, and continue ignoring client-supplied priority under R-20.

**Rejected alternative:** Raising every VIP P3 or P4 ticket to P2 would honour R-06 but reject the exclusive matrix rule in R-05. A cosmetic executive issue would then share a target with a team whose work has stopped.

**Reason:** The desk has finite response capacity. Impact and urgency directly describe disruption; status alone does not. Uniform classification makes queue treatment explainable and prevents a reporter attribute from displacing more disruptive incidents. VIP users lose the promised preferential target, which must be communicated as a deliberate service-policy choice rather than hidden as an implementation detail.

**Service owner:** The Service Desk product owner approves the priority policy and communicates withdrawal of the VIP guarantee to stakeholders; individual agents should not invent exceptions to it.

**Customer outcome:** Users with the same disruption receive the same target. VIP reporters retain P1 for organisation-wide work stoppages, but a personal cosmetic issue remains P4, so executive users bear the consequence of losing preferential treatment.
