# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from typing import Callable, Dict, Union

import zmq
from tornado.ioloop import IOLoop
from zmq import Context
from zmq.eventloop.zmqstream import ZMQStream

from maro.rl_v3.utils.distributed import bytes_to_pyobj, bytes_to_string, pyobj_to_bytes, string_to_bytes


class Worker(object):
    def __init__(
        self,
        type: str,
        idx: int,
        obj_creator: Union[Callable, Dict[str, Callable]],
        router_host: str,
        router_port: int = 10001
    ) -> None:
        self._id = f"{type}_worker.{idx}"
        self._obj_creator = obj_creator

        # ZMQ sockets and streams
        self._context = Context.instance()
        self._socket = self._context.socket(zmq.DEALER)
        self._socket.identity = string_to_bytes(self._id)
        self._router_address = f"tcp://{router_host}:{router_port}"
        self._socket.connect(self._router_address)
        print(f"Successfully connected to dispatcher at {self._router_address}")
        self._socket.send_multipart([b"", b"READY"])
        self._task_receiver = ZMQStream(self._socket)
        self._event_loop = IOLoop.current()

        # register handlers
        self._task_receiver.on_recv(self._compute)
        self._task_receiver.on_send(self.log_send_result)

        self._obj_dict: Dict[str, object] = {}

    def _compute(self, msg: list) -> None:
        obj_name = bytes_to_string(msg[1])
        req = bytes_to_pyobj(msg[-1])
        assert isinstance(req, dict)

        if obj_name not in self._obj_dict:
            creator_fn = self._obj_creator if isinstance(self._obj_creator, Callable) else self._obj_creator[obj_name]
            self._obj_dict[obj_name] = creator_fn()
            print(f"Created object {obj_name} at worker {self._id}")

        func_name, args, kwargs = req["func"], req["args"], req["kwargs"]
        func = getattr(self._obj_dict[obj_name], func_name)
        result = func(*args, **kwargs)
        self._task_receiver.send_multipart([b"", msg[1], b"", pyobj_to_bytes(result)])

    def start(self) -> None:
        self._event_loop.start()

    def stop(self) -> None:
        self._event_loop.stop()

    @staticmethod
    def log_send_result(msg: list, status: object) -> None:
        print(f"Returning result for {msg[1]}")