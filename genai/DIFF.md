---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-genai-openai 1.2b0; opentelemetry-sdk 1.45.0; openai 3.19.2"
  spec_ref: "semantic-conventions@v1.41.1"
  attributes:
    - {name: gen_ai.operation.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.provider.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.temperature, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.max_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.finish_reasons, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.id, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.input_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.output_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.top_p, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.conversation.id, emitted: false, in_spec: true, stability: development}
---
<!-- ai-generated: 100% - Codex compared an actual instrumented local model call with the versioned upstream attribute registry. -->

# Captured attributes and versioned conventions

This is the unedited OTLP JSON export of one actual OpenAI-compatible chat-completion request to Ollama serving qwen2.5:0.5b locally. It ran on 10 October 2026 through OpenAIInstrumentor, not through a hand-written span. The capture script, dependency pins and model name make the experiment reproducible. No paid provider or real API credential was used.

All ten emitted gen_ai.* attribute names exist in the [v1.41.1 registry](https://github.com/open-telemetry/semantic-conventions/blob/v1.41.1/model/gen-ai/registry.yaml) and have development stability there. In this experiment there is no attribute-name mismatch. This does not make the instrumentation stable: its exported schema URL is 1.37.0, whereas the comparison snapshot is 1.41.1. Upgrading either component requires repeating this comparison rather than assuming the common names imply identical semantics forever.

The provider label is openai because that is the client library/protocol instrumented; the endpoint and system fingerprint show that the actual inference backend is local Ollama. A dashboard labelled "OpenAI cloud usage" would misdescribe these spans even though the attribute name conforms. Model selection and response model both say qwen2.5:0.5b. The request used temperature zero and a 32-token output limit; the returned usage was 44 input tokens and 32 output tokens. The finish reason is length, so this captured response was truncated. This is telemetry evidence, not a claim that the tiny model's explanation was correct or complete.

top_p and conversation.id are defined in the reference but absent here: no top-p parameter or conversation identifier was supplied. Absent does not mean zero. A dashboard should preserve missing values and avoid treating them as a new numerical category. Token usage is provider-reported and can differ from billable usage. The capture intentionally does not record message bodies as attributes; enabling content capture would add privacy and storage considerations.

Reproduction: start an Ollama server on localhost:11434, pull qwen2.5:0.5b, install genai/requirements.txt into a virtual environment, then run python genai/capture.py. The script makes exactly one non-retried API call and flushes the file exporter. spans.json is the captured submission evidence; a rerun intentionally replaces that evidence and should be reviewed before committing. The inference container was stopped before latency measurements to avoid competing for CPU.

