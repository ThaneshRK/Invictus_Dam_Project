"""
Shared helpers for simulation engine input adapters.
"""
from typing import Any, Optional


def resolve_dataset_path(dataset: Any) -> Optional[str]:
    """
    Resolves the on-disk file path of a dataset-like object.

    Supports:
      - Real `Dataset` ORM models (`.file_path` column, `.metadata_` JSONB)
      - Test/mock contexts exposing a plain `.metadata` dict
    """
    if dataset is None:
        return None

    path = getattr(dataset, "file_path", None)
    if path:
        return path

    for attr in ("metadata_", "metadata"):
        meta = getattr(dataset, attr, None)
        if isinstance(meta, dict):
            path = meta.get("file_path")
            if path:
                return path

    return None
