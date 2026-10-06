from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


class DataLoader:
    """Loads test data rows from YAML / JSON / CSV and validates them into models."""

    @staticmethod
    def load(path: Path, model: type[M]) -> list[M]:
        suffix = path.suffix.lower()
        with path.open(encoding="utf-8") as fh:
            if suffix in {".yaml", ".yml"}:
                rows = yaml.safe_load(fh) or []
            elif suffix == ".json":
                rows = json.load(fh)
            elif suffix == ".csv":
                rows = list(csv.DictReader(fh))
            else:
                raise ValueError(f"Unsupported data file type: {path}")
        return [model.model_validate(row) for row in rows]
