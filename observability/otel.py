"""OpenTelemetry instrumentation for Anthropic SDK"""
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

_init = False


def setup():
    """Setup OpenTelemetry for Anthropic SDK - enabled when OTEL_ENABLED=1"""
    global _init

    if _init or os.getenv("OTEL_ENABLED") != "1":
        return

    provider = TracerProvider()
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    AnthropicInstrumentor().instrument()
    _init = True
