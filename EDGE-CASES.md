---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 100% - Codex drafted these explanations from the specification and observed service output; student review is required. -->
# Edge cases in the practice event log

Counts above come from POST /dora/metrics and agree with the published practice answer. The metric calculation is a pure function of the submitted log; it does not read that answer file.

## E1 - Clock skew

- What the log contains: Three first-successful-deployment/commit pairs have a deployment earlier than the commit timestamp. The service keeps all three pairs with duration zero.
- What a default definition would have done: Dropping impossible-looking observations would change the sample without informing the dashboard reader. Keeping negative durations would suggest delivery before work existed and could reward poor clock synchronisation.
- Why the rule is defensible: R-08 retains the evidence of delivery while declining to claim a negative elapsed duration. Clamping is a convention, not a correction of the true timestamp: the anomaly count keeps that uncertainty visible to the operations owner.

## E2 - Reverting a revert

- What the log contains: Two revert commits resolve transitively to their original change. The service counts 86 distinct changes across the entire log, instead of assigning independent changes to the revert commits.
- What a default definition would have done: Treating every commit as a separate delivered change would make undoing and redoing work look like additional customer value. A team measured on output could improve its apparent productivity by cycling the same change.
- Why the rule is defensible: R-06 preserves the identity of the original work through reversals. Commit-level delivery still has its own samples under R-08, but change-level ground truth starts from the earliest commit of the shared identity under R-07.

## E3 - Hotfixes outside main

- What the log contains: Four distinct off-main commit shas appear in in-window production deployments. The anomaly counts both successful and failed deployments; only successful deployments supply lead-time pairs.
- What a default definition would have done: Filtering branch names to main would hide emergency work deployed directly to production. The service owner would see a cleaner dashboard precisely when the normal delivery path had been bypassed.
- Why the rule is defensible: R-09 defines delivery by reaching the production environment, not by a naming convention. Retaining hotfixes exposes the actual response workload and does not pretend all teams use the same branching policy.

## E4 - Deployments without commits

- What the log contains: Four production deployments in the observation window have empty commit lists. They contribute to deployment counts and rate denominators but cannot provide commit lead-time samples.
- What a default definition would have done: An inner join between commits and deployments would discard them, understating production activity and changing both instability ratios. Another implementation might invent a zero lead time, which would falsely improve the median.
- Why the rule is defensible: R-10 separates deployment activity from evidence of code delivery. Configuration work can be real despite absent commit linkage. Counting it is reasonable, but it makes frequency vulnerable to empty activity, as the demonstration below shows.

## E5 - Failure with no recovery

- What the log contains: One failed production deployment has no recovery under the earliest-covering-incident rule. Seven failures contribute observed recovery durations and the eighth remains in open_failures.
- What a default definition would have done: Closing the failure at the observation-window boundary would fabricate an observed recovery. Silently dropping it from failure counts would tell the service owner that an unresolved disruption did not happen.
- Why the rule is defensible: R-12 distinguishes missing recovery evidence from completed recovery. The median describes recovered failures only, while open_failures and R-14 retain the unresolved risk. A low recovery median cannot be read as proof that all incidents were handled quickly.

## E6 - Overlapping incidents

- What the log contains: Eleven unordered pairs of incident intervals intersect. Recovery is attributed separately to each failed deployment; the earliest opening selects its covering incident, with incident id resolving ties.
- What a default definition would have done: Merging overlap into one incident would erase deployment-specific recovery attribution. Summing overlapping wall time would double-count elapsed disruption and confuse this metric with total customer downtime.
- Why the rule is defensible: R-13 measures restoration following each failed deployment. One recovery can legitimately close several failures; the units remain deployments, not incidents or hours of organisation-wide outage. The overlap anomaly warns readers that these concepts cannot be interchanged.

## Gaming demonstration

The named metric is deployment_frequency_per_day and the exploited rule is R-11, aided by R-10 counting empty deployments. In gaming/after.jsonl, the 34 successful production deployments originally inside the window move to exactly 2026-09-22T00:00:00Z, the excluded upper boundary. Their outcomes, environments, identifiers and commit links are retained. All original commits and incidents are unchanged, and no deployment moves earlier. Sixty additional successful production deployments have no linked commits. These are no-op release activities, not additional delivered features.

The service reports 42/21 = 2.0 deployments per day before and 68/21 = 3.238095 afterwards: about a 61.90% improvement, exceeding R-20's 25% margin. The 68 consist of eight original failures and sixty new empty successes. Meanwhile, ground_truth.changes_delivered falls from 65 to 0, below the R-21 threshold of 58.5. No new commits were added, so the base-only harm check has exactly the same inputs as the transformed log. The true lead-time median becomes null because no original work was successfully delivered in the window; this is absence of delivery, not zero latency.

A release manager rewarded for deployment frequency could prioritise easy no-op releases while postponing difficult customer work into the next reporting period. The frequency dashboard would reward that manager, while customers waiting for the original 65 changes receive nothing during the period. Failure and rework ratios also look better because the denominator is diluted and the real successful work is postponed. This demonstration preserves the record rather than falsifying timestamps of commits or changing failure outcomes. A responsible review should pair activity metrics with delivered-change counts, unresolved failures and qualitative customer outcomes, instead of setting frequency alone as a target.
