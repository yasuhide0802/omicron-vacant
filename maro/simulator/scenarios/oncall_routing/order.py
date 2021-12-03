# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from enum import Enum
from itertools import count

from .coordinate import Coordinate

GLOBAL_ORDER_COUNTER = count()


class OrderStatus(Enum):
    # TODO: confirm the order status
    NOT_READY = "order not ready yet"
    READY_IN_ADVANCE = "order not reach the open time but ready for service"
    IN_PROCESS = "order in process"
    IN_PROCESS_BUT_DELAYED = "order in process but delayed"
    FINISHED = "order finished"
    TERMINATED = "order terminated"


class Order:
    def __init__(
        self,
        order_id: str,
        coordinate: Coordinate,
        open_time=None,  # TODO: typehint
        close_time=None,  # TODO: typehint
        is_delivery=None  # TODO: typehint
    ) -> None:
        self.id = order_id
        self.coord = coordinate
        self.privilege = None
        # TODO: align the open time and close time with env tick
        self.open_time = open_time
        self.close_time = close_time
        self.is_delivery = is_delivery
        self.service_level = None
        self.package_num = None
        self.weight = None
        self.volume = None
        self.creation_time = None
        self.delay_buffer = None
        self._status = OrderStatus.NOT_READY

    def get_status(self, tick: int, advance_buffer: int = 0) -> OrderStatus:
        # TODO: update here or in BE?
        if self._status == OrderStatus.NOT_READY and tick >= self.open_time - advance_buffer:
            self._status = OrderStatus.READY_IN_ADVANCE
        if self._status == OrderStatus.READY_IN_ADVANCE and tick >= self.open_time:
            self._status = OrderStatus.IN_PROCESS
        if self._status == OrderStatus.IN_PROCESS and tick > self.close_time:
            self._status = OrderStatus.IN_PROCESS_BUT_DELAYED
        # TODO: logic for terminated?
        return self._status

    def set_status(self, var: OrderStatus) -> None:
        self._status = var

    def __repr__(self) -> str:
        return f"[Order]: id: {self.id}, coord: {self.coord}"
