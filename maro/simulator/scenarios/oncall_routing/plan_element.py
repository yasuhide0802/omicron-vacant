# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from dataclasses import dataclass
from typing import Optional

from .order import Order


@dataclass
class PlanElement:
    order: Order
    estimated_duration_from_last: Optional[int] = None  # Estimated duration from last stop
    actual_duration_from_last: Optional[int] = None  # Actual duration from last stop