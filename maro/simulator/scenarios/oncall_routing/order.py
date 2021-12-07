# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from enum import Enum
from itertools import count
from typing import Optional

from maro.utils import DottableDict

from .coordinate import Coordinate


class OrderIdGenerator(object):
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(OrderIdGenerator, cls).__new__(cls, *args, **kwargs)
        return cls.__instance

    def __init__(self) -> None:
        self._counter = count()

    def __iter__(self):
        return self

    def __next__(self) -> str:
        return str(next(self._counter))

    def next(self):
        return self.__next__()

    def reset(self):
        self._counter = count()


GLOBAL_ORDER_ID_GENERATOR = OrderIdGenerator()


class OrderStatus(Enum):
    NOT_READY = "order not ready yet"
    READY_IN_ADVANCE = "order not reach the open time but ready for service"
    IN_PROCESS = "order in process"
    IN_PROCESS_BUT_DELAYED = "order in process but delayed"
    COMPLETED = "order completed"
    TERMINATED = "order terminated"
    DUMMY = "dummy order, for case like rtb trigger"


class Order:
    def __init__(
        self,
        order_id: str,
        coordinate: Coordinate,
        open_time: int,
        close_time: int,
        is_delivery: Optional[bool],
        status: OrderStatus = OrderStatus.NOT_READY
    ) -> None:
        assert 0 <= open_time <= close_time < 1440

        self.id: str = order_id
        self.coord: Coordinate = coordinate
        self.privilege = None   # TODO: Enum class?
        self.open_time: int = open_time
        self.close_time: int = close_time
        self.is_delivery: bool = is_delivery
        self.service_level = None   # TODO: Enum class?
        self.package_num: Optional[int] = None
        self.weight: Optional[float] = None
        self.volume: Optional[float] = None
        self.creation_time: Optional[int] = None
        self.delay_buffer: Optional[int] = None  # TODO: keep the independent one or use a general setting
        self._status = status

    def get_status(self, tick: int, transition_config: DottableDict) -> OrderStatus:
        # TODO: fresh order status at each tick if needed
        if self._status == OrderStatus.NOT_READY and tick >= self.open_time - transition_config.buffer_before_open_time:
            self._status = OrderStatus.READY_IN_ADVANCE
        if self._status == OrderStatus.READY_IN_ADVANCE and tick >= self.open_time:
            self._status = OrderStatus.IN_PROCESS
        if self._status == OrderStatus.IN_PROCESS and tick > self.close_time:
            self._status = OrderStatus.IN_PROCESS_BUT_DELAYED
        if (
            self._status == OrderStatus.IN_PROCESS_BUT_DELAYED
            and tick > min(
                self.close_time + transition_config.buffer_after_open_time,
                transition_config.last_tick_for_order_processing
            )
        ):
            self._status = OrderStatus.TERMINATED
        return self._status

    def set_status(self, var: OrderStatus) -> None:
        self._status = var

    def __repr__(self) -> str:
        # TODO: add more information
        return (
            f"[Order]: id: {self.id}, coord: {self.coord}, status: {self._status}, "
            f"open time: {self.open_time}, close time: {self.close_time}"
        )
