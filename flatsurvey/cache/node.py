r"""
Nodes in a tree of :class:`Results`.
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
        >>> cache = Cache(pickles=None, report=None)
        >>> Node(1, cache=cache, kind=None)
        1

    """

    def __init__(self, value, cache, kind):
        self._value = value
        self._cache = cache
        self._kind = kind

    def __repr__(self):
        r"""
        Return a printable representation of this node, i.e., the underlying raw data.

        EXAMPLES::

            >>> from flatsurvey.cache import Cache
            >>> cache = Cache(pickles=None, report=None)
            >>> Node({}, cache=cache, kind=None)
            {}

        """
        return repr(self._value)

    def __getattr__(self, name):
        r"""
        Return the lazily resolved attribute ``name`` on this node.

        EXAMPLES::

            >>> from io import StringIO
            >>> from flatsurvey.cache import Cache
            >>> cache = Cache(jsons=[StringIO('{"surface": [{"type": "Ngon", "angles": [1, 2, 4], "pickle": "a1b54e02ade464584920abcbfd07faaa71afac1d5b455a56d5cf790ccf5528da"}]}')], pickles=None, report=None)
            >>> node = Node({"surface": "a1b54e02ade464584920abcbfd07faaa71afac1d5b455a56d5cf790ccf5528da"}, cache=cache, kind=None)
            >>> node.surface.type
            'Ngon'

        """
        try:
            for source in self._cache.sources():
                if source == "CACHE":
                    if isinstance(self._value, dict) and name in self._value:
                        return self._cache.make(self._value[name], name=name)

                if source == "PICKLE":
                    if isinstance(self._value, dict) and "pickle" in self._value:
                        instance = self._cache.unpickle(
                            self._value["pickle"], self._kind
                        )
                        return getattr(instance, name)

                if source == "DEFAULTS":
                    defaults = self._cache.defaults()
                    if name in defaults:
                        return defaults[name]

        except AttributeError as e:
            raise RuntimeError(e)

        raise AttributeError(f"{self} has no {name}")


class ReferenceNode(Node):
    r"""
    A node that references a node in another cache source.

    EXAMPLES::

        >>> from io import StringIO
        >>> from flatsurvey.cache import Cache
        >>> cache = Cache(jsons=[StringIO('{"surface": [{"type": "Ngon", "angles": [1, 2, 4], "pickle": "a1b54e02ade464584920abcbfd07faaa71afac1d5b455a56d5cf790ccf5528da"}]}')], pickles=None, report=None)
        >>> ReferenceNode('a1b54e02ade464584920abcbfd07faaa71afac1d5b455a56d5cf790ccf5528da', "surface", cache=cache)
        {'type': 'Ngon', 'angles': [1, 2, 4], 'pickle': 'a1b54e02ade464584920abcbfd07faaa71afac1d5b455a56d5cf790ccf5528da'}

    """

    def __init__(self, sha, section, cache):
        super().__init__(sha, cache, section)

    def _resolve(self):
        r"""
        Return the node this node resolves to.
        """
        return self._cache.get(self._kind, self._value)

    def __getattr__(self, name):
        if name == "pickle":
            return self._value

        resolved = self._resolve()
        try:
            return getattr(resolved, name)
        except AttributeError:
            return super().__getattr__(name)

    def __repr__(self):
        return repr(self._resolve())
