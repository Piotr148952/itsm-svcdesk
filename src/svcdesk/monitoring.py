# ai-generated: 100% - Codex wrote ASGI instrumentation and refined the ladder from the measured account profile.
"""One wall-time observation per HTTP response, with bounded route labels."""
from time import perf_counter
from prometheus_client import CollectorRegistry, Histogram, generate_latest

BUCKETS = (0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.15,
           0.17, 0.18, 0.19, 0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26,
           0.28, 0.3, 0.4, 0.6, 1, 2, 5)
REGISTRY = CollectorRegistry()
REQUEST_DURATION = Histogram(
    "http_server_request_duration_seconds", "Time from request arrival through response body, in seconds",
    ("http_request_method", "http_route", "http_response_status_code"),
    buckets=BUCKETS, registry=REGISTRY)


class RequestMetrics:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] == "/metrics":
            return await self.app(scope, receive, send)
        started, status, observed = perf_counter(), 500, False

        def observe():
            nonlocal observed
            if not observed:
                route = getattr(scope.get("route"), "path", "unmatched")
                REQUEST_DURATION.labels(scope["method"], route, str(status)).observe(perf_counter() - started)
                observed = True

        async def measured_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                observe()

        try:
            await self.app(scope, receive, measured_send)
        except Exception:
            observe()
            raise


def exposition():
    return generate_latest(REGISTRY)
