---
actual_minutes: 2.6610
---
<!-- ai-generated: 100% - Codex recorded tool-observed elapsed time and limitations. -->
# METR n=1 observation

Prediction: 45 minutes. Actual: 2.6610 minutes. Ratio actual/predicted: 0.06.
Start (UTC): 2026-09-26T14:32:01.0407534+00:00. End (UTC): 2026-09-26T14:34:40.7023860Z. Prediction receipt: https://github.com/swasik/itsm-2026-submissions/issues/153.

The measured feature was the stateless metrics endpoint in src/svcdesk/dora.py. Timing began after the accepted prediction receipt and before creating that file. Timing ended after the endpoint matched the full practice answer and dedicated synthetic cases passed. The complete suite at this boundary passed 72 tests: 49 existing Lab 1 tests and 23 new Lab 2 cases, including parameterised validation cases. Waiting for Docker builds, a failed test run and correction of a missing closing dictionary brace are included. There were no deliberately excluded breaks during this interval.

The prediction overestimated this observed implementation interval. This is not evidence that AI speeds up developers by that ratio: there is no unaided control, randomisation or repeated sample. The specification and fixtures had already been read before timing, and the existing API, error handlers, Docker setup and test harness were reusable. The narrow endpoint interval excludes the lifecycle exporter, gaming experiment, reasoning artifact and final release exactly as predicted. Automated tests establish conformance on these inputs, not universal correctness or human comprehension. User review of the reasoning remains separate from this implementation-time observation.
