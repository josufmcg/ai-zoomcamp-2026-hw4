import atexit
import sys

from opentelemetry import _logs, metrics, trace
from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import ConsoleLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


class CurrentStdout:
    def write(self, value: str) -> int:
        return sys.stdout.write(value)

    def flush(self) -> None:
        sys.stdout.flush()


console_output = CurrentStdout()
resource = Resource.create({"service.name": "order-tracker"})

metric_reader = PeriodicExportingMetricReader(
    ConsoleMetricExporter(out=console_output),
    export_interval_millis=5_000,
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
trace_provider = TracerProvider(resource=resource)
trace_provider.add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter(out=console_output))
)
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(
    SimpleLogRecordProcessor(ConsoleLogRecordExporter(out=console_output))
)

metrics.set_meter_provider(meter_provider)
trace.set_tracer_provider(trace_provider)
_logs.set_logger_provider(logger_provider)

meter = metrics.get_meter("order-tracker")
tracer = trace.get_tracer("order-tracker")
logger = _logs.get_logger("order-tracker")
request_counter = meter.create_counter(
    "http.server.request.count",
    unit="{request}",
    description="Number of HTTP requests",
)


def log_order_lookup(order_id: str, found: bool) -> None:
    result = "found" if found else "not_found"
    logger.emit(
        severity_number=SeverityNumber.INFO if found else SeverityNumber.WARN,
        severity_text="INFO" if found else "WARN",
        body="Order lookup completed",
        attributes={"order.id": order_id, "order.lookup.result": result},
    )


def shutdown_telemetry() -> None:
    meter_provider.shutdown()
    trace_provider.shutdown()
    logger_provider.shutdown()


atexit.register(shutdown_telemetry)
