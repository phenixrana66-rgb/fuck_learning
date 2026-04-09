from backend.app.common.schemas import AppBaseModel


class MetricSnapshot(AppBaseModel):
    name: str
    value: float
    unit: str
