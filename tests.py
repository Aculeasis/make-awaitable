#!/usr/bin/env python3

import asyncio
import time

import make_awaitable as ma


@ma.call
def call_me(time_):
    time.sleep(time_)
    return time_


@ma.contextmanager
def contextmanager_me(poll):
    def iter_():
        for x in poll:
            yield x
            time.sleep(0.02)
    try:
        yield iter_()
    finally:
        pass


@ma.iterable
def iter_me(pull):
    for x in pull:
        yield x
        time.sleep(0.05)


async def test_call(time_):
    return await call_me(time_)


async def test_contextmanager(poll):
    result = 0
    async with contextmanager_me(poll) as cm:
        async for data in cm:
            result += data
    return result


async def test_iter(poll):
    result = 0
    async for data in iter_me(poll):
        result += data
    return result


def get_tasks(context_data, iter_data):
    return [test_call(1), test_call(1), test_contextmanager(context_data), test_iter(iter_data)]


def test():
    context_data = [x for x in range(12)]
    iter_data = [x*20 for x in range(14)]

    loop = asyncio.get_event_loop()
    one_run = time.perf_counter()
    for task in get_tasks(context_data, iter_data):
        loop.run_until_complete(task)
    one_run = time.perf_counter() - one_run

    all_run = time.perf_counter()
    workers = loop.run_until_complete(asyncio.gather(*get_tasks(context_data, iter_data)))
    all_run = time.perf_counter() - all_run

    print(workers)
    print('By one: {}, by all: {}'.format(one_run, all_run))

    assert workers == [1, 1, sum(context_data), sum(iter_data)]
    assert all_run < 2 < one_run


if __name__ == '__main__':
    test()
