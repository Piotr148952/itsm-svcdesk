---
lab3_first_draft:
  source: ai
  tool: "Codex, GPT-6, desktop app, 10 October 2026"
  ladder: [0.005, 0.01, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18, 0.2, 0.22, 0.24, 0.26, 0.28, 0.3, 0.33, 0.36, 0.4, 0.44, 0.48, 0.53, 0.58, 0.64, 0.7, 0.8, 1, 2, 5]
  verdict: pending-measurement
  evidence: {p99_seconds: null, bucket: [], relative_width: null}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: null, bucket: [], relative_width: null}
---
<!-- ai-generated: 100% - Codex supplied the initial proposal before measurement; evidence will be added after load 3. -->
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

## Measurement pending

This proposal is committed before the first profile measurement. No verdict about this ladder has yet been inferred from measured data.
