from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class DataType(str, Enum):
    SCALAR = "scalar"
    TIMESERIES = "timeseries"
    DISTRIBUTION = "distribution"
    GRAPH = "graph"
    UNKNOWN = "unknown"

class Granularity(str, Enum):
    GLOBAL = "global"
    GROUP = "group"
    INDIVIDUAL = "individual"
    TEMPORAL = "temporal"
    UNKNOWN = "unknown"

@dataclass
class DataMetric:
    category: str
    file_name: str
    file_path: str
    description: Optional[str] = None
    data_type: DataType = DataType.UNKNOWN
    granularity: Granularity = Granularity.UNKNOWN
    sample_size: int = 0
    sample_data: Optional[Any] = None  # A small sample for context

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "file_name": self.file_name,
            "description": self.description,
            "data_type": self.data_type.value,
            "granularity": self.granularity.value,
            "sample_size": self.sample_size,
            # "sample_data": self.sample_data  # Omit sample data from dict to keep context small
        }

def infer_data_type(data_sample: Any) -> DataType:
    """
    Infers the data type based on the structure of the data payload.
    """
    if isinstance(data_sample, (int, float)):
        return DataType.SCALAR
    elif isinstance(data_sample, list):
        # Check if it's a list of numbers (timeseries) or objects
        if data_sample and isinstance(data_sample[0], (int, float)):
            return DataType.TIMESERIES
        return DataType.UNKNOWN
    elif isinstance(data_sample, dict):
        # Check for distribution patterns (e.g., ECharts/Highcharts style)
        if "xAxis" in data_sample and "series" in data_sample:
            return DataType.DISTRIBUTION
        # Check for another distribution pattern (categories/values)
        if "categories" in data_sample and "values" in data_sample:
            return DataType.DISTRIBUTION
        # Check for graph patterns
        if "nodes" in data_sample and "links" in data_sample:
            return DataType.GRAPH
        return DataType.UNKNOWN
    return DataType.UNKNOWN

def infer_granularity(record: Dict[str, Any]) -> Granularity:
    """
    Infers the granularity based on the keys present in the record.
    """
    keys = record.keys()
    
    if "agent_id" in keys:
        return Granularity.INDIVIDUAL
    elif "group_name" in keys or "group_id" in keys:
        return Granularity.GROUP
    elif "step" in keys or "round" in keys or "tick" in keys:
        # If no group/agent but has time, it's likely global temporal data
        return Granularity.TEMPORAL
    else:
        return Granularity.GLOBAL

def scan_processed_data(processed_dir: Union[str, Path]) -> List[DataMetric]:
    """
    Scans the processed directory for JSON files and profiles them.
    """
    processed_path = Path(processed_dir)
    metrics: List[DataMetric] = []

    if not processed_path.exists():
        logger.warning(f"Processed directory not found: {processed_path}")
        return metrics

    for file_path in processed_path.glob("*.json"):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                content = json.load(f)
            
            # Check if it follows the standard structure with "file_info" and "data"
            if not isinstance(content, dict) or "data" not in content:
                continue
            
            data_list = content.get("data")
            if not isinstance(data_list, list):
                continue

            file_info = content.get("file_info", {})
            category = file_info.get("category", file_path.stem.replace("_", " "))
            description = file_info.get("description")
            
            sample_size = len(data_list)
            data_type = DataType.UNKNOWN
            granularity = Granularity.UNKNOWN
            sample_payload = None

            if sample_size > 0:
                first_record = data_list[0]
                if isinstance(first_record, dict):
                    # Granularity inference
                    granularity = infer_granularity(first_record)
                    
                    # Data Type inference (look at the 'data' key inside the record)
                    payload = first_record.get("data")
                    sample_payload = payload
                    if payload is not None:
                        data_type = infer_data_type(payload)
            
            metric = DataMetric(
                category=category,
                file_name=file_path.name,
                file_path=str(file_path.absolute()),
                description=description,
                data_type=data_type,
                granularity=granularity,
                sample_size=sample_size,
                sample_data=sample_payload
            )
            metrics.append(metric)

        except Exception as e:
            logger.error(f"Failed to process file {file_path.name}: {e}")
            continue

    return metrics

if __name__ == "__main__":
    # CLI Test
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Data Profiling Tool")
    parser.add_argument("dir", help="Directory to scan")
    args = parser.parse_args()
    
    results = scan_processed_data(args.dir)
    print(f"Found {len(results)} metrics:")
    for m in results:
        print(f"\n[Category]: {m.category}")
        print(f"  File: {m.file_name}")
        print(f"  Type: {m.data_type.value}")
        print(f"  Granularity: {m.granularity.value}")
        print(f"  Sample Size: {m.sample_size}")
        print(f"  Description: {m.description}")
