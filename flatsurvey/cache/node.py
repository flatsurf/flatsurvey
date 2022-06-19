r"""
A node in a tree of :class:`Results`.
"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2022 Julian Rüth
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


class Node:
    r"""
    Adds lazy-loading to a primitive item from the cache.

    EXAMPLES::

        >>> from flatsurvey.cache import Cache
        >>> cache = Cache(pickles=None)
        >>> Node(1, cache=cache)
        1

    """

    def __init__(self, value, cache, kind):
        self._value = value
        self._cache = cache
        self._kind = kind

    def make(self, value, name, kind=None):
        if kind is None:
            kind = name

        if value is None:
            return None

        if isinstance(value, list):
            if name.endswith('s'):
                name = name[:-1]
            else:
                name = None
            return [self.make(v, name=name) for v in value]

        if isinstance(value, str) and name in ["surface"]:
            return ReferenceNode(value, "surface", cache=self._cache)

        if isinstance(value, (bool, int, str)):
            return value

        return Node(value, cache=self._cache, kind=kind)

    def __repr__(self):
        r"""
        Return a printable representation of this node, i.e., the underlying raw data.

        EXAMPLES::

            >>> from flatsurvey.cache import Cache
            >>> cache = Cache(pickles=None)
            >>> Node({}, cache=cache)
            {}

        """
        return repr(self._value)

    def __getattr__(self, name):
        r"""
        Return the lazily resolved attribute ``name`` on this node.

        EXAMPLES::

            >>> from flatsurvey.cache import Cache
            >>> cache = Cache(pickles=None)
            >>> node = Node({"surface": '177156c4-1794-11eb-b7bd-0600cfa33284'}, cache=cache)
            >>> node.surface.type

        """
        try:
            for source in self._cache.sources():
                if source == "CACHE":
                    if isinstance(self._value, dict) and name in self._value:
                        return self.make(self._value[name], name=name)

                if source == "PICKLE":
                    if isinstance(self._value, dict) and "pickle" in self._value:
                        instance = self._cache.unpickle(self._value["pickle"], self._kind)
                        return getattr(instance, name)

                if source == "DEFAULTS":
                    defaults = self._cache.defaults()
                    if name in defaults:
                        return defaults[name]

        except AttributeError as e:
            raise RuntimeError(e)

        raise AttributeError(name)


class ReferenceNode(Node):
    r"""
    A node that references a node in another cache source.

    EXAMPLES::

        >>> from flatsurvey.cache import Cache
        >>> cache = Cache(pickles=None)
        >>> ReferenceNode('177156c4-1794-11eb-b7bd-0600cfa33284', "surface", cache=cache)
        ...

        # TODO

    """

    def __init__(self, reference, kind, cache):
        super().__init__(reference, cache)
        self._kind = kind
