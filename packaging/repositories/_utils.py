# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
from __future__ import absolute_import, division, print_function

import functools

from .base import Request, Response
from effect import Effect, sync_perform, sync_performer, ParallelEffects
from effect.async import perform_parallel_async as perform_parallel_serially
from effect import base_dispatcher, ComposedDispatcher, TypeDispatcher


from txeffect import (
    make_twisted_dispatcher, deferred_performer, perform as twisted_performer)
from twisted.internet.defer import inlineCallbacks, returnValue


@sync_performer
def _blocking_request(dispatcher, intent):
    from requests import get
    response = get(intent.url)
    return Response(
        content=response.content,
        headers=response.headers,
    )

_blocking_dispatcher = ComposedDispatcher([
    TypeDispatcher({Request: _blocking_request
                    ParallelEffects, perform_parallel_serially,
                    }),
    base_dispatcher,
])


def blocking_engine(effect):
    "Run an effect synchronously"
    return sync_perform(_blocking_dispatcher, effect)


def _turn_twisted_headers_to_dict(headers):
    return {k: v[0] for (k, v) in headers.getAllRawHeaders().items()}


@deferred_performer
@inlineCallbacks
def _twisted_request(reactor, dispatcher, intent):
    from treq import get
    response = yield get(intent.url, reactor=reactor)
    returnValue(Response(
        content=(yield response.get()),
        headers=_turn_twisted_headers_to_dict(response.headers),
    ))


def get_twisted_engine(reactor):
    dispatcher = ComposedDispatcher(
        TypeDispatcher({
            Request: functools.partial(_twisted_request, reactor)}),
        make_twisted_dispatcher(reactor),
        base_dispatcher,
    )

    def twisted_engine(effect):
        "Run an effect using twisted."
        return twisted_performer(dispatcher, effect)
    return twisted_engine


def engined(f):
    "Turn an effect using function into one that uses a specific performer."
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        engine = kwargs.pop('engine', blocking_engine)
        effect = f(*args, **kwargs)
        result = engine(effect)
        return result

    wrapper.effectfully = f
    return wrapper


@engined
def request(url):
    return Effect(Request(url))
