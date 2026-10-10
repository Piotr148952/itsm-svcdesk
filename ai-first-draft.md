---
lab3_first_draft:
  source: ai
  tool: "Codex, GPT-6, desktop app, 10 October 2026"
  ladder: [0.005, 0.01, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18, 0.2, 0.22, 0.24, 0.26, 0.28, 0.3, 0.33, 0.36, 0.4, 0.44, 0.48, 0.53, 0.58, 0.64, 0.7, 0.8, 1, 2, 5]
  verdict: confirmed
  evidence: {p99_seconds: 0.2118, bucket: [0.2, 0.22], relative_width: 0.09443}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.2118, bucket: [0.04, 0.5], relative_width: 2.17186}
---
<!-- ai-generated: 100% - Codex supplied the pre-measurement proposal and wrote the verdicts from the actual load 3 results. -->
# Initial monitoring proposal

## Prompt

For Laboratory 3, propose initial histogram bucket boundaries in seconds and a Prometheus alert rule for GET /kb/search in svcdesk. The endpoint calls an external index exactly once per request. No measurement of this account's latency profile has been made yet. Give a concrete starting ladder and alert, and identify assumptions that need measurement.

## Answer

Use this initial ladder, in seconds: [0.005, 0.01, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18, 0.2, 0.22, 0.24, 0.26, 0.28, 0.3, 0.33, 0.36, 0.4, 0.44, 0.48, 0.53, 0.58, 0.64, 0.7, 0.8, 1, 2, 5]. It uses 30 finite boundaries and concentrates resolution between 100 and 800 milliseconds. This is a starting hypothesis, not evidence that the dependency's p99 lies there. The coarse tail above one second will need redesign if the measured p99 falls there. Measure open-loop latency, then narrow the boundaries around a band containing the observed p99 and include the chosen latency SLI threshold exactly.

As an initial availability alert, assume a 99% objective, count 5xx responses as bad, and require both a one-hour and five-minute error ratio above a burn rate of 14.4. Keep the route filter in both numerator and denominator. Hold the condition for five minutes before paging. Here is the rule:

```yaml
- alert: KbSearchAvailabilityFast
  expr: |
    (sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search",http_response_status_code=~"5.."}[1h])) / sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search"}[1h])) > 14.4 * (1 - 0.99))
    and
    (sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search",http_response_status_code=~"5.."}[5m])) / sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search"}[5m])) > 14.4 * (1 - 0.99))
  for: 5m
  labels: {service: svcdesk, slo: availability, severity: P1}
  annotations:
    summary: "Knowledge-base search failures are consuming the availability budget rapidly"
```

The 99% objective is provisional: the index's own failure rate may already exceed its budget. Choose an attainable objective after measurement, add a slower burn alert for chat, and test firing onset, a sub-threshold burn and recovery. A percentile alert alone does not express how quickly a request-based error budget is consumed.

## Measurement and revision

The prompt and answer above were committed and pushed in e7c2c2f before any profile measurement. The first real checker 0.8.0 load on 10 October 2026 used login Piotr148952: 60 seconds at 40 requests/s after warm-up. It returned 2,398 responses, including seven 502s; client p50 was 39.5 ms, p95 72.5 ms, p99 211.8 ms, p99.9 233.1 ms. Direct upstream p99 was 199.9 ms. The initial server histogram estimated p99 at 209.3 ms.

The draft is confirmed on this sample: p99 falls in (200, 220] ms, whose 20 ms width is 9.44% of p99. This is a measurement-based verdict, not a claim that an unmeasured AI guess is reliable. The supplied flawed ladder instead places the same p99 in (40, 500] ms: 460 / 211.8 = 217.19%, far beyond the 20% limit. A percentile anywhere inside that huge interval would require an unjustified interpolation assumption, especially across the distinct fast and slow modes.

The final ladder uses 27 finite boundaries. It spends more resolution on the observed body and gives 10 ms spacing from 170 to 260 ms, covering substantially more than a +/-10% band around the measured p99. The initial ladder's unused fine spacing above 300 ms was removed. Boundaries at 300 ms (our SLI threshold), 400 ms, 600 ms, 1 s, 2 s and 5 s retain visibility into regressions and timeout failures.

The initial alert was revised too: the final availability objective is 98%, with burn rates 10 (1 h / 5 min) and 3 (6 h / 30 min), both held for 5 min. Seven upstream-related failures in this run are a finite sample, not proof of a fixed failure probability. We retain budget for the dependency's failures and operating variation. See slo.md for the chosen budget arithmetic and trade-offs. The AI draft remains verbatim above so this revision is auditable.
