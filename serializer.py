"""
serializer.py

Production-ready serializer for FastAPI.

Supports

- numpy
- pandas
- datetime
- decimal
- UUID
- Plotly
- Pydantic
- dataclass
- sets
- tuples
- bytes

Author:
Progressive AI Chatbot
"""

from __future__ import annotations

import math
import uuid
import decimal
import dataclasses

from datetime import (
    datetime,
    date,
    time
)

from typing import Any

import numpy as np
import pandas as pd


# -------------------------------------------------------
# MAIN ENTRY
# -------------------------------------------------------

def make_json_serializable(obj: Any):

    """
    Recursively converts any Python object into JSON-safe types.
    """

    # ---------------------------------------------------
    # None
    # ---------------------------------------------------

    if obj is None:
        return None

    # ---------------------------------------------------
    # Primitive Types
    # ---------------------------------------------------

    if isinstance(obj, (str, int, float, bool)):
        if isinstance(obj, float):

            if math.isnan(obj):
                return None

            if math.isinf(obj):
                return None

        return obj

    # ---------------------------------------------------
    # UUID
    # ---------------------------------------------------

    if isinstance(obj, uuid.UUID):
        return str(obj)

    # ---------------------------------------------------
    # Decimal
    # ---------------------------------------------------

    if isinstance(obj, decimal.Decimal):
        return float(obj)

    # ---------------------------------------------------
    # datetime/date/time
    # ---------------------------------------------------

    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()

    # ---------------------------------------------------
    # NumPy Scalars
    # ---------------------------------------------------

    if isinstance(obj, np.integer):
        return int(obj)

    if isinstance(obj, np.floating):
        return float(obj)

    if isinstance(obj, np.bool_):
        return bool(obj)

    # ---------------------------------------------------
    # NumPy Arrays
    # ---------------------------------------------------

    if isinstance(obj, np.ndarray):
        return [
            make_json_serializable(v)
            for v in obj.tolist()
        ]

    # ---------------------------------------------------
    # Pandas Timestamp
    # ---------------------------------------------------

    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()

    # ---------------------------------------------------
    # Pandas Timedelta
    # ---------------------------------------------------

    if isinstance(obj, pd.Timedelta):
        return str(obj)

    # ---------------------------------------------------
    # Pandas Series
    # ---------------------------------------------------

    if isinstance(obj, pd.Series):
        return make_json_serializable(
            obj.to_dict()
        )

    # ---------------------------------------------------
    # Pandas DataFrame
    # ---------------------------------------------------

    if isinstance(obj, pd.DataFrame):

        return [
            make_json_serializable(r)
            for r in obj.to_dict("records")
        ]

    # ---------------------------------------------------
    # Pydantic V2
    # ---------------------------------------------------

    if hasattr(obj, "model_dump"):

        return make_json_serializable(
            obj.model_dump(exclude_none=True)
        )

    # ---------------------------------------------------
    # Dataclass
    # ---------------------------------------------------

    if dataclasses.is_dataclass(obj):

        return make_json_serializable(
            dataclasses.asdict(obj)
        )

    # ---------------------------------------------------
    # Dictionary
    # ---------------------------------------------------

    if isinstance(obj, dict):

        return {
            str(k): make_json_serializable(v)
            for k, v in obj.items()
        }

    # ---------------------------------------------------
    # List / Tuple / Set
    # ---------------------------------------------------

    if isinstance(obj, (list, tuple, set)):

        return [
            make_json_serializable(v)
            for v in obj
        ]

    # ---------------------------------------------------
    # Bytes
    # ---------------------------------------------------

    if isinstance(obj, bytes):

        return obj.decode(
            "utf-8",
            errors="ignore"
        )

    # ---------------------------------------------------
    # Objects having __dict__
    # ---------------------------------------------------

    if hasattr(obj, "__dict__"):

        return make_json_serializable(
            vars(obj)
        )

    # ---------------------------------------------------
    # Fallback
    # ---------------------------------------------------

    return str(obj)


