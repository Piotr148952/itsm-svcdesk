<!-- ai-generated: 100% - Codex documented the actual checker load through a configured Toxiproxy. -->
# Where the additional latency is measured

On 10 October 2026, a downstream latency toxic of 200 ms with zero jitter and toxicity 1.0 was installed in Toxiproxy 2.12.0. The proxy forwarded port 8666 to svcdesk:8080. The real checker load used login Piotr148952, a five-second warm-up and 60 seconds open-loop at 40 requests/s with the client target http://host.docker.internal:8666.

It measured client p99 420.9 ms and the service histogram's own p99 210.7 ms over the same run. Their difference is 210.2 ms. The client saw 2,391 responses (2,388 HTTP 200 and three HTTP 502). The extra delay is downstream of the ASGI response timer, so the service can record completion while the proxy is still holding bytes from the client. Open-loop client latency also includes scheduling, connection and network costs. The local inference container was stopped before the experiment.

The roughly 10.2 ms excess above the configured 200 ms is not another programmed toxic: host networking, client queuing and histogram interpolation can contribute. The difference between two marginal p99 estimates is not the p99 of paired per-request differences. The server's estimate interpolates between finite bucket counts, whereas the load generator uses its client samples. Repeating the run will vary, even with zero toxic jitter.

The ordinary server ladder deliberately does not resolve the proxied client p99: 420.9 ms lies in the coarse (400,600] ms server bucket. Nor should the server timer suddenly include an external proxy's wait. The direct unproxied profile remains the basis of the service ladder and Core validation. Client-side or edge monitoring is needed to observe this particular user-visible degradation; a server-only latency SLO can remain green while users wait longer.

## Reproduce on Windows

Start the optional proxy with:

    docker compose --profile gap up -d --build svcdesk kb-index toxiproxy

Create the proxy and toxic using PowerShell (Toxiproxy's API rejects browser-like user agents, so the explicit curl agent is required):

    Invoke-RestMethod http://localhost:8474/proxies -UserAgent 'curl/8.0' -Method Post -ContentType application/json -Body '{"name":"svcdesk","listen":"0.0.0.0:8666","upstream":"svcdesk:8080","enabled":true}'
    Invoke-RestMethod http://localhost:8474/proxies/svcdesk/toxics -UserAgent 'curl/8.0' -Method Post -ContentType application/json -Body '{"type":"latency","stream":"downstream","toxicity":1.0,"attributes":{"latency":200,"jitter":0}}'
    .\itsmlab.ps1 load 3 --base-url http://host.docker.internal:8666

If the proxy already exists, inspect its configuration before reusing it; do not add a second latency toxic accidentally. gap.json contains the measured seconds, while Toxiproxy's attributes are in milliseconds. The grader creates its own proxy and repeats this experiment from the recorded toxic; the local running containers are not submission evidence.

