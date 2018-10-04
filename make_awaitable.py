#!/usr/bin/env python3

import asyncio
import contextlib
import threading
import time


def call(func):
    def wrapper(*args, **kwargs):
            return MakeMeCall(func, *args, **kwargs)
    return wrapper


def contextmanager(func):
    def wrapper(*args, **kwargs):
            return MakeMeContextIterable(func, *args, **kwargs)
    return wrapper


def iterable(func):
    def wrapper(*args, **kwargs):
            return MakeMeIterable(func, *args, **kwargs)
    return wrapper


class EventTS(asyncio.Event):
    # TODO: clear() method
    def set(self):
        # FIXME: The _loop attribute is not documented as public api!
        self._loop.call_soon_threadsafe(super().set)


class MakeMeCall(threading.Thread):
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._data = None
        self._end = None
        self.start()

    def run(self):
        self._data = self._func(*self._args, **self._kwargs)
        self._end = True

    def __await__(self):
        while self._end is time.sleep(0.001):
            yield
        try:
            return self._data
        finally:
            self.join()


class MakeMeIterable(threading.Thread):
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._data = None
        self._end = None

        self._work = False
        self._wait = EventTS()
        self._next = threading.Event()

    def run(self):
        try:
            for data in self._func(*self._args, **self._kwargs):
                self._data = data
                self._wait.set()
                self._next.wait()
                self._next.clear()
                if not self._work:
                    break
        finally:
            self._wait.set()
            self._end = True

    def __aiter__(self):
        self._work = True
        self.start()
        return self

    def __aexit__(self, *_):
        join = self._work
        self._work = False
        self._end = True
        self._wait.set()
        self._next.set()
        if join:
            self.join()
        return self

    async def _stop_anext(self):
        self.__aexit__()
        raise StopAsyncIteration

    async def __anext__(self):
        await self._wait.wait()
        if self._end:
            await self._stop_anext()
        try:
            return self._data
        finally:
            self._wait.clear()
            self._next.set()


class MakeMeContextIterable(MakeMeIterable):
    def __init__(self, func, *args, **kwargs):
        super().__init__(func, *args, **kwargs)

    def run(self):
        try:
            with self._call(self._func, *self._args, **self._kwargs) as read:
                for data in read:
                    self._data = data
                    self._wait.set()
                    self._next.wait()
                    if not self._work:
                        break
                    self._next.clear()
        finally:
            self._wait.set()
            self._end = True

    @staticmethod
    @contextlib.contextmanager
    def _call(func, *args, **kwargs):
        return func(*args, **kwargs)

    def __aenter__(self):
        return self

    def __await__(self):
        yield
        return self

    async def _stop_anext(self):
        raise StopAsyncIteration
