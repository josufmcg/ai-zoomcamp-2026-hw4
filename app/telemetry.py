import atexit
import os

from opentelemetry import _logs, metrics, trace
from opentelemetry._logs import SeverityNumber
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


resource = Resource.create({"service.name": "order-tracker"})
endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

metric_readers = []
span_processors = []
log_record_processors = []
if endpoint:
    metric_readers.append(
        PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=endpoint),
            export_interval_millis=5_000,
        )
    )
    span_processors.append(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    log_record_processors.append(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint))
    )

meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
trace_provider = TracerProvider(resource=resource)
logger_provider = LoggerProvider(resource=resource)
for span_processor in span_processors:
    trace_provider.add_span_processor(span_processor)
for log_record_processor in log_record_processors:
    logger_provider.add_log_record_processor(log_record_processor)

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
