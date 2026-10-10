---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 30d
  slis:
    availability:
      objective: 0.98
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search",http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.02, minutes: 864}
    latency:
      objective: 0.99
      threshold_seconds: 0.3
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk",http_route="/kb/search",le="0.3"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
  alerts:
    - {alert: KbSearchAvailabilityFast, sli: availability, burn_rate: 10, long_window: 1h, short_window: 5m}
    - {alert: KbSearchAvailabilitySlow, sli: availability, burn_rate: 3, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 100% - Codex wrote and checked these decisions against the actual Piotr148952 load measurement. -->

# SLO for GET /kb/search

## Availability

At least 98% of requests to this route should finish without a 5xx response over a rolling 30 days. The denominator includes all responses, including validation errors: 4xx responses represent a successfully enforced client contract. It excludes other routes, health checks and metrics scrapes. The rate queries aggregate status and method labels into one series.

In the first account-specific load, seven of 2,398 responses were 502 (0.292%). The index's injected failures become 502s because this service makes exactly one upstream call and cannot repair the dependency. A 99.9% objective would already fail this sample; 98% allows headroom for dependency variation while still making sustained failure visible. A single minute cannot establish a 30-day distribution: deployment measurements and accumulated request counts must be reviewed before tightening the objective.

The budget is 1 - 0.98 = 0.02 of requests. Thirty days are 43,200 minutes, so its time-equivalent is 864 minutes. This is a request-based budget: the minutes are an equivalence under constant traffic, not permission for 14.4 hours of outage at arbitrary peak load.

## Latency

At least 99% of all route responses should complete in at most 300 ms over the same 30 days. This includes error responses, so fast failures can satisfy latency but still spend the separate availability budget. A 300 ms boundary exists exactly in the histogram and the query uses Prometheus 3's label text le="0.3".

The first run measured p50 39.5 ms, p95 72.5 ms and p99 211.8 ms. The slow mode appears around 175-242 ms, substantially separated from the common 30-60 ms responses; direct upstream p99 was 199.9 ms. A 300 ms threshold leaves roughly 88 ms above measured p99 for ordinary scheduling and network variation without disguising a multi-second regression. All reported sample latencies were below it. The 99% target allows occasional slow outliers and remains an honest future canary gate at a threshold below one second. It is not guaranteed by one load run.

The latency budget is 0.01 of requests, or 432 minutes at constant traffic. The ASGI timer spans arrival through response-body transmission and includes waiting for the index; it cannot see queuing and network delay before arrival or after the last server send.

## Alerts

| Alert | SLI | Burn rate | Long / short window | Budget used at threshold over long window | Notification |
|---|---|---:|---|---|---|
| KbSearchAvailabilityFast | availability | 10 | 1 h / 5 min | 10 x 60 / 43,200 = 1.389% | P1 page |
| KbSearchAvailabilitySlow | availability | 3 | 6 h / 30 min | 3 x 360 / 43,200 = 2.5% | P2 chat |

These percentages describe sustained threshold burn over the long window; they are not an exact historical budget charge at the first firing instant. Both comparisons must hold for five minutes, so brief spikes do not page. Recovery of the short window clears the condition even while the long window still reflects earlier failures.

The fast alert requires over 20% failed requests in both windows. At ten times sustainable burn the full budget would last three days; an eight-hour overnight delay would consume about 11.1% of the monthly budget if that rate persisted. Waking a person has a cost, but that failure rate makes the service unusable to many users. The slow alert requires over 6% failures; at three times burn the budget lasts ten days and an eight-hour delay spends about 3.33%. It goes to chat for deliberate investigation rather than a second page.

A 98% objective is not a desired failure rate. These are severe-budget-burn notifications, not a promise to ignore smaller chronic loss. A dashboard exposes ordinary error ratio and attainment for routine review. No traffic is not interpreted as perfect service: the rate ratios become absent/undefined when the denominator is zero; synthetic monitoring would be a separate signal.

## Buckets

The final 27 finite boundaries in seconds are [0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.15, 0.17, 0.18, 0.19, 0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.28, 0.3, 0.4, 0.6, 1, 2, 5], plus the implicit +Inf bucket. The measured 211.8 ms p99 falls in (210, 220] ms, width 10 ms / 211.8 ms = 4.72%. The +/-10% band is 190.62-232.98 ms; the 10 ms spacing resolves that entire band and extends to 260 ms to tolerate sampling variation.

Lower boundaries describe the typical response body, while a few coarse tail boundaries reveal major regressions. Three seconds is the upstream timeout; the five-second bucket covers timeout responses with overhead. Each response increments one histogram observation; labels are only method, matched route template and status. Query text and ticket IDs never become labels. Histogram quantiles interpolate within buckets and are estimates, unlike the client distribution; agreement in one run does not eliminate interpolation error.

