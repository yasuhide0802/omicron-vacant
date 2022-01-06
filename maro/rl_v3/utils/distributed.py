# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import asyncio
import inspect
import pickle
from functools import wraps
from typing import Callable, Tuple

import zmq
from zmq.asyncio import Context

# serialization and deserialization for messaging
DEFAULT_MSG_ENCODING = "utf-8"


def string_to_bytes(s: str) -> bytes:
    return s.encode(DEFAULT_MSG_ENCODING)


def bytes_to_string(bytes_: bytes) -> str:
    return bytes_.decode(DEFAULT_MSG_ENCODING)


def pyobj_to_bytes(pyobj) -> bytes:
    return pickle.dumps(pyobj)


def bytes_to_pyobj(bytes_: bytes) -> object:
    return pickle.loads(bytes_)


def coroutine(func) -> Callable:
    """Wrap a synchronous callable to allow ``await``'ing it"""
    @wraps(func)
    async def coroutine_wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return func if asyncio.iscoroutinefunction(func) else coroutine_wrapper


def remote_method(obj_name: str, func_name: str, dispatcher_address) -> Callable:
    async def remote_call(*args, **kwargs) -> object:
        req = {"func": func_name, "args": args, "kwargs": kwargs}
        context = Context.instance()
        sock = context.socket(zmq.REQ)
        sock.identity = string_to_bytes(obj_name)
        sock.connect(dispatcher_address)
        sock.send(pyobj_to_bytes(req))
        print(f"sent request {func_name} for {obj_name}")
        result = bytes_to_pyobj(await sock.recv())
        print(f"result for request {func_name} for {obj_name}: {result}")
        sock.close()
        return result

    return remote_call


class RemoteObj(object):
    def __init__(self, name: str, dispatcher_address: Tuple[str, int]) -> None:
        self._name = name
        host, port = dispatcher_address
        self._dispatcher_address = f"tcp://{host}:{port}"

    def __getattribute__(self, attr_name: str) -> object:
        # Ignore methods that belong to the parent class
        try:
            return super().__getattribute__(attr_name)
        except AttributeError:
            pass

        return remote_method(self._name, attr_name, self._dispatcher_address)


class CoroutineWrapper(object):
    def __init__(self, obj: object) -> None:
        self._obj = obj

    def __getattribute__(self, attr_name: str) -> object:
        # Ignore methods that belong to the parent class
        try:
            return super().__getattribute__(attr_name)
        except AttributeError:
            pass

        attr = getattr(self._obj, attr_name)
        return coroutine(attr) if inspect.ismethod(attr) else attr