r"""
Access cached results from previous runs.

Currently, the only cache we support is a plain-text database stored in .json
files and some accompanying Python pickles. It would be fairly trivial to
change that and allow for other similar systems as well (and we at some point
supported a GraphQL backend but it turned out to be impractical.)

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "local-cache", "--help")  # doctest: +NORMALIZE_WHITESPACE
    Usage: worker local-cache [OPTIONS]
      A readonly cache of previous results, read from local JSON files.
    Options:
      -j, --json PATH    JSON files or directories to read cached data from
      -p, --pickles DIR  directory of pickle files to resolve references in JSON
                         files
      --help             Show this message and exit.

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2025 Julian Rüth
#
#  flatsurvey is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  flatsurvey is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurvey. If not, see <https://www.gnu.org/licenses/>.
# *********************************************************************

from pathlib import Path
from typing import Any, Literal

import click

from flatsurvey.cache.pickles import Pickles
from flatsurvey.cache.result_set import ResultSet
from flatsurvey.pipeline import Bindings
from flatsurvey.ui import Command, GroupedCommand

CacheEntry = dict[str, Any]
Source = Literal["CACHE", "DEFAULTS", "PICKLE"]


class Cache(Command):
    r"""
    A readonly cache of previous results, read from local JSON files.

    INPUT:

    - ``cache`` -- a dict or ``None`` (default: ``None``); the underlying data
      in the cache, typically parsed from JSON files. This is a dictionary from
      strings, the sections of the cache such as ``"orbit_closure"`` to a list
      of results in that section. If ``None``, the cache is empty.

    - ``pickles`` -- a :class:`Pickles`` object or ``None`` (default:
      ``None``); a source of serialized data. Each entry in ``cache`` may for
      space reasons only hold limited information about an object and defer to
      a pickle under a ``"pickle"`` key. E.g., when storing the unfolding of a
      triangle, we might only hold the angles as a triple of integers and refer
      to a pickle which holds the actual unfolding for more complex queries to
      the surface. If ``None``, then pickles referenced in ``cache`` cannot be
      resolved.

    EXAMPLES::

        >>> Cache(cache={})
        local-cache

    """

    def __init__(
        self,
        cache: dict[str, list[CacheEntry]] | None = None,
        pickles: Pickles | None = None,
    ):
        self._cache = cache or {}
        self._pickles = pickles or Pickles()

        # The last tuple in this list specifies from which source cache
        # requests get resolved, see sources().
        self._sources: list[tuple[Source, ...]] = [("CACHE", "DEFAULTS", "PICKLE")]

        # The last dict in this list gives the current defaults that are used
        # to resolve properties from a cache entry that cannot be found in the
        # cache without actually loading the pickle (which is often very
        # expensive.) See sources() and defaults() for details.
        self._defaults: list[CacheEntry] = [{}]

        # A cache mapping the values of the ``"pickle"`` fields of entries back
        # to the cache entries, i.e., self._shas[entry["pickle"]] == entry
        # holds for each entry of the section of the _cache.
        self._shas: dict[str, CacheEntry] = {}

    @staticmethod
    def create(bindings: Bindings):
        r"""
        Return a ``Cache`` instance from the configuration registered in ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> bindings = Bindings()
            >>> invoke_subcommand(Cache.click, bindings=bindings)
            >>> Cache.create(bindings)
            local-cache

        """
        with bindings.scope(Cache) as scoped:
            return Cache(
                cache=scoped.get("cache", default=lambda: {}),
                pickles=scoped.get("pickles", default=lambda: None),
            )

    @staticmethod
    @click.command(
        name="local-cache",
        cls=GroupedCommand,
        group="Cache",
        help=__doc__.split("INPUT")[0],  # type: ignore
    )
    @click.option(
        "--json",
        "-j",
        metavar="PATH",
        multiple=True,
        type=click.Path(path_type=Path, exists=True),
        help="JSON files or directories to read cached data from",
    )
    @click.option(
        "--pickles",
        "-p",
        metavar="DIR",
        type=click.Path(path_type=Path, exists=True),
        default=None,
        help="directory of pickle files to resolve references in JSON files",
    )
    @Bindings.click
    def click(bindings: Bindings, json: list[Path], pickles):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(Cache.click)

        """
        if pickles is not None:
            from flatsurvey.cache.pickles import DirectoryPickleProvider

            pickles = DirectoryPickleProvider(pickles)

        with bindings.scope(Cache) as scoped:
            scoped.define(cache=Cache.load(json), pickles=pickles)

    @staticmethod
    def load(paths: list[Path]) -> dict:
        r"""
        Load previous results from ``paths`` and return them as a dict of
        results by subject.

        If ``paths`` contains a directory, its contents are read recursively.

        Note that configuration of the runs, i.e., anything that is not a list
        is copied into each result.

        EXAMPLES::

            >>> from pathlib import Path
            >>> from tempfile import TemporaryDirectory

            >>> with TemporaryDirectory() as tmpdir:
            ...     tmpdir = Path(tmpdir)
            ...     with open(tmpdir / "a.json", "w") as json: _ = json.write('{"subject": [{"result": true}], "surface": "111"}')
            ...     with open(tmpdir / "b.json", "w") as json: _ = json.write('{"subject": [{"result": false}], "surface": "3413"}')
            ...     Cache.load([tmpdir / "a.json", tmpdir / "b.json"])
            {'subject': [{'surface': '111', 'result': True}, {'surface': '3413', 'result': False}]}

        """
        from collections import defaultdict

        subjects = defaultdict(lambda: [])

        for parsed in Cache._load_parse(paths):
            for subject, values in Cache._load_create_subjects(parsed).items():
                subjects[subject].extend(values)

        return dict(subjects)

    @staticmethod
    def _load_parse(paths: list[Path]):
        r"""
        Helper method for :meth:`load` that presents the JSON input as an
        iterator over parsed dicts.

        EXAMPLES::

            >>> from pathlib import Path
            >>> from tempfile import TemporaryDirectory

            >>> with TemporaryDirectory() as tmpdir:
            ...     tmpdir = Path(tmpdir)
            ...     with open(tmpdir / "a.json", "w") as json: _ = json.write('{"subject": {"result": true}}')
            ...     with open(tmpdir / "b.json", "w") as json: _ = json.write('{"subject": {"result": false}}')
            ...     list(Cache._load_parse([tmpdir / "a.json", tmpdir / "b.json"]))
            [{'subject': {'result': True}}, {'subject': {'result': False}}]

        """
        seen = set()

        for path in paths:
            for json in path.rglob("*.json") if path.is_dir() else [path]:
                if json in seen:
                    continue
                seen.add(json)

                with open(json, "r") as input:
                    import orjson

                    data = input.read().strip()
                    if not data:
                        continue

                    try:
                        yield orjson.loads(data)
                    except Exception as e:
                        print(f"Failed to parse {json}, {e}. Ignoring.")

    @staticmethod
    def _load_create_subjects(parsed: dict):
        r"""
        Helper method for :meth:`load` that rewrites the dict ``parsed`` into a
        subject centered dict.

        EXAMPLES::

            >>> Cache._load_create_subjects({})
            {}

        Survey configuration is copied into each result::

            >>> Cache._load_create_subjects({
            ...     "surface": "some-surface",
            ...     "seed": 1337,
            ...     "orbit-closure": [{"dense": None}, {"dense": True}]
            ... })
            {'orbit-closure': [{'surface': 'some-surface', 'seed': 1337, 'dense': None}, {'surface': 'some-surface', 'seed': 1337, 'dense': True}]}

        Note that anything that isn't a list is considered configuration, see :meth:`Json.result`.

        """
        configuration = {}
        subjects = {}

        for key, value in parsed.items():
            if isinstance(value, list):
                subjects[key] = value
            else:
                configuration[key] = value

        # Copy configuration into each result if missing.
        subjects = {
            subject: [dict(**configuration, **result) for result in results]
            for subject, results in subjects.items()
        }

        return subjects

    def sources(self, *sources: Source):
        r"""
        Set the sources from which the cache should operate.

        Returns a context. Instruct the cache to read from the given sources as
        long as the context is active.

        If no arguments are given, return the sources the cache is currently
        using.

        EXAMPLES:

        Normally, the cache will try to read from cached data. If none is
        available, it will fall back to :meth:`defaults` if any were specified, if
        these are not available, it will try to reconstruct the cached pickle
        (which can be very slow)::

            >>> cache = Cache()
            >>> cache._sources[-1]
            ('CACHE', 'DEFAULTS', 'PICKLE')

        We can change the order temporarily::

            >>> with cache.sources("DEFAULTS"):
            ...     cache._sources[-1]
            ('DEFAULTS',)

        """
        if len(sources) == 0:
            return self._sources[-1]

        from contextlib import contextmanager

        @contextmanager
        def with_sources():
            self._sources.append(sources)
            try:
                yield None
            finally:
                assert self._sources[-1] is sources
                self._sources.pop()

        return with_sources()

    def defaults(self, defaults: dict):
        r"""
        Set the defaults used for keys that are missing from a node.

        Returns a context. The ``defaults`` are used for the lifetime of this
        context.

        EXAMPLES:

            >>> cache = Cache(cache={"A": [{}]})

            >>> cache.get("A").type
            Traceback (most recent call last):
            ...
            AttributeError: cached result has no 'type'

            >>> with cache.defaults({"type": "B"}):
            ...     cache.get("A").type
            'B'

        """
        from contextlib import contextmanager

        @contextmanager
        def with_defaults():
            self._defaults.append(defaults)
            try:
                yield None
            finally:
                assert self._defaults[-1] is defaults
                self._defaults.pop()

        return with_defaults()

    def get(self, section: str | type | Command, sha: str | None = None) -> ResultSet:
        r"""
        Return the results for ``section``.

        EXAMPLES:

        Cached results are automatically requested by a goal with
        :meth:`Goal._consume_cache` which calls this method.

        However, the cache can also be queried manually. Let's suppose that we
        have a cache from previous runs::

            >>> cache = { "orbit-closure": [
            ...     { "dense": None, "surface": {"type": "Ngon", "angles": [3, 4, 13], "pickle": "hash-0-of-a-3413"}, "pickle": "hash-0-of-an-orbit-closure"},
            ...     { "dense": None, "surface": {"type": "Ngon", "angles": [3, 4, 13], "pickle": "hash-1-of-a-3413"}, "pickle": "hash-1-of-an-orbit-closure"},
            ...     { "surface": {"type": "Ngon", "angles": [1, 2, 13], "pickle": "hash-0-of-a-1213"}, "pickle": "hash-2-of-an-orbit-closure"},
            ...     { "dense": True, "surface": {"type": "Ngon", "angles": [1, 2, 13], "pickle": "hash-1-of-a-1213"}, "pickle": "hash-3-of-an-orbit-closure"},
            ...     { "dense": True, "surface": {"type": "Ngon", "angles": [1, 2, 11], "pickle": "hash-0-of-a-1211"}, "pickle": "hash-4-of-an-orbit-closure"},
            ... ]}

        We provide some pickles for the sake of showcasing the features of the
        cache. Usually, these pickles are loaded from a directory on the
        filesystem and not injected statically like this::

            >>> from pickle import dumps
            >>> from flatsurvey.cache import Pickles
            >>> from flatsurvey.cache.pickles import StaticPickleProvider
            >>> pickles = Pickles([
            ...     StaticPickleProvider(dumps({"dense": True}), digest="hash-2-of-an-orbit-closure"),
            ... ])

            >>> cache = Cache(cache=cache, pickles=pickles)

        Then we can query all cached results for a goal::

            >>> from flatsurvey.jobs import OrbitClosure
            >>> cache.get(OrbitClosure)
            5 cached results

        We can filter the results further::

            >>> len(cache.get(OrbitClosure).filter(lambda entry: entry.dense is not True))
            2

        Or, if we only want results for a specific surface (the ``cache=cache``
        parameter is optional but speeds up searches a lot)::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 2, 4))
            >>> cache.get(OrbitClosure).filter(surface.cache_predicate(exact=False, cache=cache))
            0 cached results
            >>> surface = Ngon((3, 4, 13))
            >>> cache.get(OrbitClosure).filter(surface.cache_predicate(exact=False, cache=cache))
            2 cached results

        The above returns the results for any ngon with such angles. To only
        accept results for surfaces that are exactly the same, we can use the
        ``exact`` keyword; however this is only implemented for triangles currently::

            >>> cache.get(OrbitClosure).filter(surface.cache_predicate(exact=True))
            2 cached results

        We can also only look at results for surfaces with certain properties::

            >>> cache.get(OrbitClosure).filter(lambda entry: entry.dense is not True)
            2 cached results

        Note that the above operation could be expensive because it needs to
        restore the pickle of the orbit closure where "dense" was not included
        in the cache. Instead, we can tell the cache to ignore pickles for
        "dense" and assume a default value instead::

            >>> with cache.defaults({"dense": None}):
            ...     with cache.sources("CACHE", "DEFAULTS"):
            ...         cache.get(OrbitClosure).filter(lambda entry: entry.dense is not True)
            3 cached results

        """
        if isinstance(section, (type, Command)):
            section = section.name()

        if sha is not None:
            entries = self._from_sha(section, sha)
        else:
            entries = self._cache.get(section, [])

        sources = []
        for source in self._sources[-1]:
            if source == "DEFAULTS":
                sources.append(self._defaults[-1])
            elif source == "CACHE":
                sources.append("CACHE")
            elif source == "PICKLE":
                if self._pickles:
                    sources.append(self._pickles)
            else:
                raise NotImplementedError

        return ResultSet(entries, sources=sources)

    def _from_sha(self, section, sha):
        r"""
        Return the entries whose pickle SHA is ``sha`` from the ``section`` of
        the cache.

        EXAMPLES::

            >>> cache = Cache({"surface": [{"pickle": "some-hash"}]})

            >>> cache._from_sha("surface", "some-hash")
            [{'pickle': 'some-hash'}]

        """
        if section not in self._shas:
            self._shas[section] = {}
            for entry in self._cache.get(section, []):
                self._shas[section].setdefault(sha, [])
                self._shas[section][sha].append(entry)

        return self._shas[section].get(sha, [])


__test__ = {
    # doctests of click do not run unless explicitly mentioned here due to the click decorator.
    "Cache.click": Cache.click.__doc__,
}
