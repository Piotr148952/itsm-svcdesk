# ai-generated: 100% - Codex wrote a reproducible instrumented call to a local Ollama model.
"""Run with Ollama serving qwen2.5:0.5b at localhost:11434; no paid API key required."""
from pathlib import Path
from openai import OpenAI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.json.file import FileSpanExporter
from opentelemetry.instrumentation.genai.openai import OpenAIInstrumentor

provider = TracerProvider(resource=Resource.create({"service.name": "svcdesk-genai-lab"}))
provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(str(Path(__file__).with_name("spans.json")))))
trace.set_tracer_provider(provider)
OpenAIInstrumentor().instrument()
with OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama-local", max_retries=0) as client:
    response = client.chat.completions.create(
        model="qwen2.5:0.5b", temperature=0, max_tokens=32,
        messages=[{"role": "user", "content": "Explain in one sentence what an HTTP 502 error means."}])
    print(response.choices[0].message.content)
provider.force_flush()
provider.shutdown()
