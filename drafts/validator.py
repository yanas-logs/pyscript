import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("DataValidator")

REQUIRED_KEYS = ("source", "item_id", "metrics")


def validate_record(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate required fields and basic types of a single record."""
    errors: List[str] = []

    for key in REQUIRED_KEYS:
        if key not in record or record[key] in (None, ""):
            errors.append(f"Missing or empty field: {key}")

    if "metrics" in record and not isinstance(record["metrics"], dict):
        errors.append("Field 'metrics' must be a dictionary")

    return (len(errors) == 0, errors)


def filter_valid_records(
    records: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split records into valid and invalid lists with error reasons."""
    valid: List[Dict[str, Any]] = []
    invalid: List[Dict[str, Any]] = []

    for rec in records:
        is_valid, errors = validate_record(rec)
        if is_valid:
            valid.append(rec)
        else:
            logger.warning(f"Invalid record {rec.get('item_id')}: {', '.join(errors)}")
            invalid.append({"record": rec, "errors": errors})

    return valid, invalid


def summarize_by_source(records: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count valid records per data source."""
    summary: Dict[str, int] = {}
    for rec in records:
        src = str(rec.get("source", "unknown"))
        summary[src] = summary.get(src, 0) + 1
    return summary
