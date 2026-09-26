<!-- ai-generated: 100% - Codex compared the receipted specification with implementation and observed tests. -->
# Convergence report

The implementation was started after specs receipt issue 140 accepted commit 70cdeaa70654294f119707865a318c8bc80b92c4. The specification remains specs/svcdesk.md. There is no implementation under src/ in that receipted commit except the template README.

R-01, R-02 and R-25 converge: FastAPI serves JSON, health identifies svcdesk, and missing routes/tickets return JSON errors. R-03, R-18 and R-20 converge through strict creation models, UUIDs, ignored unknown/server-owned fields and a common validation envelope. Tests reject boolean, floating-point and string impact values as well as excessive lengths.

R-04 and R-05 converge under C3=matrix. All nine matrix combinations are tested. R-06's VIP floor is deliberately rejected; the VIP attribute is retained and a P1 VIP stays P1. DECISIONS.md states who loses preferential treatment and why.

R-07, R-08 and R-11 converge through transactional state transitions, recorded event instants and original deadlines retained after reopening. C2=immutable honours R-09 and rejects only closed-ticket reopening in R-10. Resolved tickets reopen exactly at seven days and are refused one second later. Tests exercise invalid shortcuts and every action against a closed ticket.

R-12 through R-17 converge with the declared C1 exception: R-13 applies to P2-P4, and R-14 supplies continuous P1 targets. All eight API vectors pass, including the closing-time tie, winter time and the autumn DST weekend. Boundary tests establish that equality is not a breach, late acknowledgement remains breached, timely completion remains timely, and pause begins exactly at closing. Reopening clears completion timestamps without extending due instants.

R-19 and R-21 converge: list filters intersect, request clocks accept offsets, reject malformed values and never impose monotonic time. A request without a test header returns to actual UTC time after earlier artificial clocks. This was checked through the HTTP interface, not by calling internal arithmetic functions.

R-22 and R-24 are implemented by a build-based Compose service with a healthcheck and dependencies installed at image build time. All persistence uses a named volume, with no bind mounts. R-23 was additionally checked by creating a ticket, restarting the service container and fetching the same identifier successfully. This matters even though Tier A does not enforce persistence for Lab 1.

Validation observed before this report: the tests Compose profile exited zero with ITSMLAB-TESTS: passed=49 failed=0. The course checker is also run against the committed tree before tagging. The tests service needs only SVCDESK_URL at runtime and does not install dependencies or contact other services.

No undeclared functional deviations were identified. This is a small teaching service: listing scans all stored tickets, there is no authentication, and holidays are intentionally not excluded from business hours. These are scope boundaries, not claims of production readiness. Only the three explicitly documented contradictory clauses are rejected.
