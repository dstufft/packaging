# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
from __future__ import absolute_import, division, print_function

import functools

import attr

from .base import BaseRepository
from ._utils import engined
from effect import parallel
from effect.do import do, do_return
from itertools import chain


@attr.s(cmp=False, slots=True)
class FilteredRepository(BaseRepository):

    repository = attr.ib()
    _predicate = attr.ib(repr=False, hash=False)

    def fetch(self, project):
        fetcher = self.repository.fetch(project)

        original_get_files = fetcher.get_files

        @functools.wraps(fetcher.get_files)
        def filtered_get_files(*args, **kwargs):
            files = original_get_files(*args, **kwargs)
            return list(filter(self._predicate, files))

        fetcher.get_files = filtered_get_files

        return fetcher


@attr.s(cmp=False, slots=True)
class MultiRepository(BaseRepository):

    repositories = attr.ib()

    @engined
    @do
    def fetch(self, project):
        results = []

        results = yield parallel(
            repository.fetch.effectfully(project)
            for repository in self.repositories
        )
        do_return(chain(*results))
