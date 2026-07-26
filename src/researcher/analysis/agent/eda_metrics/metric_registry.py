from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


class MetricType:
    time_series = "time_series"
    distribution = "distribution"
    categorical = "categorical"
    summary = "summary"
    unknown = "unknown"


@dataclass
class MetricFlags:
    insufficient_data: bool = False
    unknown_type: bool = False
    reason: Optional[str] = None


@dataclass
class MetricRecord:
    metric_name: str
    file_path: str
    raw_rows: List[Dict[str, Any]] = field(default_factory=list)
    type: str = MetricType.unknown
    flags: MetricFlags = field(default_factory=MetricFlags)


class MetricRegistry:
    def __init__(self) -> None:
        self._items: Dict[str, MetricRecord] = {}

    def add(self, record: MetricRecord) -> None:
        self._items[record.metric_name] = record

    def get(self, metric_name: str) -> Optional[MetricRecord]:
        return self._items.get(metric_name)

    def list_metrics(self) -> List[str]:
        return sorted(list(self._items.keys()))

    def items(self) -> List[MetricRecord]:
        return [self._items[k] for k in self.list_metrics()]


__all__ = [
    "MetricType",
    "MetricFlags",
    "MetricRecord",
    "MetricRegistry",
]

