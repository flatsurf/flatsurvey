r"""
Trees of cached results from previous survey runs.

EXAMPLES:

A result set is the object that is normally returned from querying our cache::

    >>> from flatsurvey.cache import Cache
    >>> cache = Cache({"orbit_closure": [{"dense": None}, {"dense": True}]})
    >>> result_set = cache.get("orbit_closure")
    >>> result_set
    2 cached results

Accessing a result set usually just works when the result set agrees on a
value::

    >>> result_set.dense
    Traceback (most recent call last):
    ...
    AttributeError: 'dense' is inconsistent in this cached result set, found True != None

Otherwise, we can iterate manually over the result set::

    >>> [result.dense for result in result_set]
    [None, True]

Run a predicate on the result set::

    >>> result_set.filter(lambda result: result.dense)
    {'dense': True}

Or choose a policy of access that does not require argeement on the values::

    >>> result_set = result_set.latest
    >>> result_set.dense
    True

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2022-2025 Julian Rüth
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

from typing import Literal

from flatsurvey.cache.pickles import Pickles

Quorum = Literal["UNIQUE", "LATEST"]


class ResultSet:
    r"""
    A set of results as returned by our :class:`Cache`.

    EXAMPLES::

        >>> ResultSet(rows=[{"dense": True}, {"dense": None}], sources=["CACHE"])
        2 cached results

    """

    def __init__(
        self,
        rows: list[dict],
        sources: list[Literal["CACHE"] | dict | Pickles],
        quorum: Quorum = "UNIQUE",
    ):
        self._rows = rows
        self._sources = sources
        self._quorum: Quorum = quorum

    def __repr__(self):
        r"""
        Return a printable representation of this set of cached results.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": True}, {"dense": None}], sources=["CACHE"])
            >>> results
            2 cached results

            >>> results[0]
            {'dense': True}

        """
        if len(self) == 1:
            return repr(self._rows[0])
        else:
            return f"{len(self)} cached results"

    def __len__(self):
        r"""
        Return the number of cached results in this set.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": True}, {"dense": None}], sources=["CACHE"])
            >>> len(results)
            2

        """
        return len(self._rows)

    def __getattr__(self, name):
        if not self._rows:
            raise AttributeError("no results found in cache")

        if self._quorum == "UNIQUE":
            return self._getattr_unique(name)
        if self._quorum == "LATEST":
            return self._getattr_latest(name)

        raise NotImplementedError(self._quorum)

    def _getattr_unique(self, name):
        r"""
        Return the value of the attribute ``name`` if all results agree on its
        value.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": True, "surface": "3413"}, {"dense": None, "surface": "3413"}], sources=["CACHE"])
            >>> results.dense
            Traceback (most recent call last):
            ...
            AttributeError: 'dense' is inconsistent in this cached result set, found None != True
            >>> results.surface
            '3413'

        """
        values = iter(
            ResultSet._getattr(row, name, self._sources) for row in self._rows
        )
        value = next(values)

        for other in values:
            if other != value:
                raise AttributeError(
                    f"'{name}' is inconsistent in this cached result set, found {other} != {value}"
                )

        return value

    def _getattr_latest(self, name):
        r"""
        Return the value of the attribute ``name`` that the most recent result reported.

        Note that we do not consider timestamps here but just consider the last
        result read to be the most recent one.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": True, "surface": "3413"}, {"dense": None, "surface": "3413"}], sources=["CACHE"], quorum="LATEST")
            >>> results.dense
            >>> results.surface
            '3413'

        """
        return ResultSet._getattr(self._rows[-1], name, self._sources)

    def __getitem__(self, key):
        r"""
        Return a view of a subset of these cached results.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": True}, {"dense": None}], sources=["CACHE"])

            >>> results[1]
            {'dense': None}
            >>> results[-1]
            {'dense': None}
            >>> results[1:]
            {'dense': None}

        """
        rows = self._rows[key]
        if not isinstance(key, slice):
            rows = [rows]
        return ResultSet(rows, sources=self._sources, quorum=self._quorum)

    def __dir__(self):
        r"""
        Return an iterable of reasonable attributes to query on this result
        set.

        The underlying logic is a bit ad-hoc but works reasonably well for
        tab-completion in practice.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": True}, {"dense": None, "version": "2", "dimension": 2}], sources=["CACHE", {"version": "unknown", "platform": "unknown"}])

            >>> 'dense' in dir(results)
            True
            >>> 'foo' in dir(results)
            False
            >>> 'dimension' in dir(results)
            True
            >>> 'version' in dir(results)
            True
            >>> 'platform' in dir(results)
            False

        """
        yield from super().__dir__()
        yield from {key for row in self._rows for key in row.keys()}

    @staticmethod
    def _getattr(
        row: dict, name: str, sources: list[Literal["CACHE"] | dict | Pickles]
    ):
        r"""
        Helper method for :meth:`__getattr__`.

        Return the value of ``name`` in the single cache dict ``row`` applying
        strategy ``source``.

        EXAMPLES::

            >>> row = {"dense": True}
            >>> ResultSet._getattr(row, "dense", ["CACHE"])
            True

            >>> ResultSet._getattr(row, "surface", ["CACHE"])
            Traceback (most recent call last):
            ...
            AttributeError: cached result has no 'surface'

        When defaults are provided they can be used as a fallback::

            >>> ResultSet._getattr(row, "surface", ["CACHE", {"surface": "3413"}])
            '3413'

        When pickles are provided we can try to use them as a fallback::

            >>> from pickle import dumps
            >>> from flatsurvey.cache import Pickles
            >>> from flatsurvey.cache.pickles import StaticPickleProvider
            >>> pickles = Pickles([
            ...     StaticPickleProvider(dumps({"angles": (3, 4, 13)}), digest="surface-hash"),
            ... ])
            >>> row = {"pickle": "surface-hash"}
            >>> ResultSet._getattr(row, "angles", ["CACHE", pickles])
            (3, 4, 13)

        """
        for source in sources:
            if source == "CACHE":
                try:
                    result = row[name]
                except KeyError:
                    continue
            elif isinstance(source, dict):
                try:
                    result = source[name]
                except KeyError:
                    continue
            elif isinstance(source, Pickles):
                try:
                    pickle = row["pickle"]
                except KeyError:
                    continue

                instance = source.load(pickle)

                try:
                    result = instance[name]
                except KeyError:
                    continue
            else:
                raise NotImplementedError("result set does not support this source yet")

            if isinstance(result, dict):
                return ResultSet([result], sources=sources, quorum="UNIQUE")

            return result

        raise AttributeError(f"cached result has no '{name}'")

    def __hash__(self):
        r"""
        Result sets are currently not hashable.

        EXAMPLES::

            >>> results = ResultSet(rows=[], sources=[])
            >>> hash(results)
            Traceback (most recent call last):
            ...
            TypeError

        """
        raise TypeError

    def __eq__(self, other):
        r"""
        Return whether this set of results is indistinguishable from ``other``.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": None}, {"dense": None}, {"dense": True}], sources=["CACHE"])
            >>> results == results
            True
            >>> results[0] == results[1]
            True
            >>> results[0] == results[2]
            False
            >>> results[:2] == results[0]
            False

        """
        if self is other:
            return True

        if not isinstance(other, ResultSet):
            return False

        if self._sources != other._sources:
            return False

        if self._quorum != other._quorum:
            return False

        return self._rows == other._rows

    def __bool__(self):
        r"""
        Return whether this set of results is non-empty.

        EXAMPLES::

            >>> results = ResultSet(rows=[], sources=[])
            >>> bool(results)
            False

        """
        return bool(self._rows)

    @property
    def latest(self):
        r"""
        Return this result set but such that accessing its attributes returns
        the latest of its results.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": None}, {"dense": True}], sources=["CACHE"])
            >>> results.dense
            Traceback (most recent call last):
            ...
            AttributeError: 'dense' is inconsistent in this cached result set, found True != None
            >>> results.latest.dense
            True

        """
        return ResultSet(self._rows, self._sources, quorum="LATEST")

    @property
    def unique(self):
        r"""
        Return this result set but such that accessing its attributes returns
        the value that all entries of the set agree upon.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": None}, {"dense": True}], sources=["CACHE"])
            >>> results = results.latest
            >>> results.dense
            True
            >>> results.unique.dense
            Traceback (most recent call last):
            ...
            AttributeError: 'dense' is inconsistent in this cached result set, found True != None

        """
        return ResultSet(self._rows, self._sources, quorum="UNIQUE")

    def filter(self, predicate):
        r"""
        Return the result set obtained by filtering out all the results that do
        not satisfy ``predicate``.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": True}, {"dense": None}], sources=["CACHE"])
            >>> results.filter(lambda result: result.dense)
            {'dense': True}

        """
        rows = [result._rows[0] for result in self if predicate(result)]
        return ResultSet(rows, sources=self._sources, quorum=self._quorum)

    def any(self, predicate) -> bool:
        r"""
        Return whether any row satisfies the ``predicate``.

        This is just a shorthand for the very command ``bool(filter())``.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": True}, {"dense": None}], sources=["CACHE"])
            >>> results.any(lambda result: result.dense)
            True

        """
        return bool(self.filter(predicate))

    def all(self, predicate) -> bool:
        r"""
        Return whether any row satisfies the ``predicate``.

        This is just a shorthand for the very command ``bool(filter(not))``.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": True}, {"dense": None}], sources=["CACHE"])
            >>> results.all(lambda result: result.dense)
            False

        """
        return not self.any(lambda *args, **kwargs: not predicate(*args, **kwargs))

    def __iter__(self):
        r"""
        Return an iterator over the results in this set.

        The results are returned as results sets again with only a single
        element each.

        EXAMPLES::

            >>> results = ResultSet(rows=[{"dense": True}, {"dense": None}], sources=["CACHE"])
            >>> list(results)
            [{'dense': True}, {'dense': None}]

        """
        for row in self._rows:
            yield ResultSet([row], sources=self._sources, quorum="UNIQUE")

    def keys(self) -> set[str]:
        r"""
        Return the attributes that are supported by this result set.

        EXAMPLES::

            >>> results = ResultSet(rows=[
            ...     {"a": True, "b": True, "c": True},
            ...     {"a": True, "b": False}
            ... ], sources=["CACHE"])
            >>> results.keys()
            {'a'}

            >>> results = results.latest
            >>> sorted(results.keys())
            ['a', 'b']

        """
        keys = {key for row in self._rows for key in row}

        def is_functional(key):
            try:
                getattr(self, key)
                return True
            except AttributeError:
                return False

        return {key for key in keys if is_functional(key)}
