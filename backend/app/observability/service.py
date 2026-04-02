from backend.app.observability.schemas import MetricSnapshot


def default_metrics() -> list[MetricSnapshot]:
    return [
        MetricSnapshot(name="parse_latency", value=0.0, unit="ms"),
        MetricSnapshot(name="qa_latency", value=0.0, unit="ms"),
    ]
