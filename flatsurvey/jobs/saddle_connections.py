r"""
The saddle connections on a translation surface.

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker import worker
    >>> invoke(worker, "saddle-connections", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker saddle-connections [OPTIONS]
      Saddle connections on the surface.
    Options:
      --bound INTEGER              stop search after all saddle connections up to
                                   that length have been processed  [default: no
                                   bound]
      --limit INTEGER              stop search after that many saddle connections
                                   have been considered  [default: no limit]
      --ignore-fundamental-domain  search in all directions and not only in a
                                   fundamental domain modulo the symmetries of the
                                   surface
      --help                       Show this message and exit.

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

import click

from flatsurvey.pipeline import Bindings, Producer
from flatsurvey.reporting import Report
from flatsurvey.surfaces import Surface
from flatsurvey.ui import Command
from flatsurvey.ui.group import GroupedCommand


class SaddleConnections(Producer, Command):
    r"""
    Saddle connections on the surface.
    """

    DEFAULT_BOUND = None
    DEFAULT_LIMIT = None
    DEFAULT_FUNDAMENTAL_DOMAIN = True

    def __init__(
        self,
        surface: Surface,
        report: Report | None = None,
        limit=DEFAULT_LIMIT,
        bound=DEFAULT_BOUND,
        fundamental_domain=DEFAULT_FUNDAMENTAL_DOMAIN,
    ):
        super().__init__(report=report)

        self._surface = surface
        self._limit = limit
        self._bound = bound
        self._fundamental_domain = fundamental_domain

        self._count = 0

        # We initialize the connections lazily so we do not instantiate the
        # surface until it is requested. This helps against memory leaks when
        # resolving results from the cache.
        self.__connections = None
        self.__connections_iterator = None

    @staticmethod
    def create(bindings: Bindings):
        r"""
        Return a ``SaddleConnections`` instance from the configuration registered in ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> invoke_subcommand(SaddleConnections.click, bindings=bindings)
            >>> SaddleConnections.create(bindings)
            saddle-connections

        """
        with bindings.scope(SaddleConnections) as scoped:
            return SaddleConnections(
                surface=bindings.get(Surface),
                report=bindings.get(Report),
                limit=scoped.get(
                    "limit", default=lambda: SaddleConnections.DEFAULT_LIMIT
                ),
                bound=scoped.get(
                    "bound", default=lambda: SaddleConnections.DEFAULT_BOUND
                ),
                fundamental_domain=scoped.get(
                    "fundamental_domain",
                    default=SaddleConnections.DEFAULT_FUNDAMENTAL_DOMAIN,
                ),
            )

    @staticmethod
    @click.command(
        name="saddle-connections",
        cls=GroupedCommand,
        group="Intermediates",
        help=__doc__.split("EXAMPLES")[0],  # type: ignore
    )
    @click.option(
        "--bound",
        type=int,
        default=DEFAULT_BOUND,
        help="stop search after all saddle connections up to that length have been processed  [default: no bound]",
    )
    @click.option(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="stop search after that many saddle connections have been considered  [default: no limit]",
    )
    @click.option(
        "--ignore-fundamental-domain",
        is_flag=True,
        help="search in all directions and not only in a fundamental domain modulo the symmetries of the surface",
    )
    @Bindings.click
    def click(bindings: Bindings, bound, limit, ignore_fundamental_domain):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(SaddleConnections.click)

        """
        with bindings.scope(SaddleConnections) as scoped:
            scoped.define(
                bound=bound,
                limit=limit,
                fundamental_domain=not ignore_fundamental_domain,
            )

    def randomize(self, lower_bound=0):
        r"""
        Take the saddle connections produced from a random sample of
        connections of length at least ``lower_bound``. (Instead of normally
        taking them just by length increasing.)

        See
        https://github.com/flatsurf/flatsurf/blob/master/libflatsurf/flatsurf/saddle_connections_sample.hpp#L32
        for details.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> invoke_subcommand(SaddleConnections.click, bindings=bindings)
            >>> sc = SaddleConnections.create(bindings)

            >>> import asyncio
            >>> asyncio.run(sc.produce())
            'NOT_EXHAUSTED'

            >>> sc._current > 64
            False

        ::

            >>> sc.randomize(lower_bound=64)

            >>> import asyncio
            >>> asyncio.run(sc.produce())
            'NOT_EXHAUSTED'

            >>> sc._current > 64
            True

        """
        self._reset(
            self._surface.surface()
            .pyflatsurf()
            .codomain()
            .flat_triangulation()
            .connections()
            .sample()
            .lowerBound(lower_bound)
        )

    def _reset(self, connections):
        r"""
        Reset the internal source of saddle connections to ``connections``.

        This is a helper to switch the saddle connections from being iterated
        by length increasing or randomly.
        """
        if self._bound is not None:
            connections = connections.bound(self._bound)

        if self._limit is not None:
            from itertools import islice

            connections = islice(connections, 0, self._limit)

        # We keep an explicit reference to the pyflatsurf object to avoid segfault due to too eager cleanup
        self.__connections = connections
        self.__connections_iterator = iter(self.__connections)

    def _produce(self):
        r"""
        Find another saddle connection on this surface and record it in
        ``_current``.

        EXAMPLES:

        Normally, we produce saddle connections by length but only in a
        fundamental domain, i.e., modulo, :meth:`Surface.symmetries`::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> from flatsurvey.surfaces.ngons import Ngon
            >>> bindings = Bindings()
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> invoke_subcommand(SaddleConnections.click, bindings=bindings)
            >>> sc = SaddleConnections.create(bindings)

            >>> import asyncio
            >>> asyncio.run(sc.produce())
            'NOT_EXHAUSTED'
            >>> sc._current
            -1

            >>> asyncio.run(sc.produce())
            'NOT_EXHAUSTED'
            >>> sc._current
            2

            >>> asyncio.run(sc.produce())
            'NOT_EXHAUSTED'
            >>> sc._current
            (3, (3*c ~ 5.1961524)) from 2 to -2

        We can change this to instead sample saddle connections randomly::

            >>> sc.randomize(0)
            >>> asyncio.run(sc.produce())
            'NOT_EXHAUSTED'

        We can only iterate over all saddle connections, even if they are
        repeated modulo symmetries of the surface::

            >>> bindings = Bindings()
            >>> invoke_subcommand(Ngon.click, "-a", "1", "-a", "1", "-a", "1", bindings=bindings)
            >>> invoke_subcommand(SaddleConnections.click, "--ignore-fundamental-domain", bindings=bindings)
            >>> sc = SaddleConnections.create(bindings)

            >>> asyncio.run(sc.produce())
            'NOT_EXHAUSTED'
            >>> sc._current
            1

            >>> asyncio.run(sc.produce())
            'NOT_EXHAUSTED'
            >>> sc._current
            -1

            >>> asyncio.run(sc.produce())
            'NOT_EXHAUSTED'
            >>> sc._current
            2

        And again sample randomly without fundamental domain constraints::

            >>> sc.randomize(0)
            >>> asyncio.run(sc.produce())
            'NOT_EXHAUSTED'

        """
        if self.__connections_iterator is None:
            connections = (
                self._surface.surface()
                .pyflatsurf()
                .codomain()
                .flat_triangulation()
                .connections()
                .byLength()
            )

            if self._fundamental_domain:
                import pyflatsurf.vector

                V = pyflatsurf.vector.Vectors(self._surface.surface().base_ring())  # type: ignore
                start, end = [V(v).vector for v in self._surface.fundamental_sector]  # type: ignore
                if start != end:
                    connections = connections.sector(start, end)

            self._reset(connections)

        assert self.__connections_iterator is not None

        try:
            self._current = next(self.__connections_iterator)
        except StopIteration:
            return "EXHAUSTED"

        self._count += 1

        self._report.progress(source=self, what="connections", count=self._count)
        return "NOT_EXHAUSTED"


__test__ = {
    # doctests of click do not run unless explicitly mentioned here due to the click decorator.
    "SaddleConnections.click": SaddleConnections.click.__doc__,
}
