r"""
Schedules jobs on the local machine as the load permits it.
"""
#*********************************************************************
#  This file is part of flatsurf.
#
#        Copyright (C) 2020 Julian Rüth
#
#  Flatsurf is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Flatsurf is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurf. If not, see <https://www.gnu.org/licenses/>.
#*********************************************************************

class Scheduler:
    r"""
    A simple scheduler that splits a survey into commands that are run on the local
    machine when the load admits it.

    >>> Scheduler(sources=[], targets=[])

    """
    def __init__(self, sources, targets):
        self.sources = sources
        self.targets = targets

    def start(self):
        r"""
        Run the scheduler until it has run out of jobs to schedule.

        >>> scheduler = Scheduler(sources=[], targets=[])
        >>> scheduler.start()

        """
        for source in self.sources:
            for item in source:
                self._schedule(item, self.targets)

    def _schedule(self, source, targets):
        r"""
        Schedule a single job, i.e., have all ``targets`` computed for a ``source``.

        >>> scheduler = Scheduler(sources=[], targets=[], dry_run=True)
        >>> scheduler._schedule(Ngon([1, 1, 1]), [OrbitClosure])

        """
        command = self._render_command(source, targets)
        self._enqueue(command)

    def _render_command(self, source, targets):
        r"""
        Return the command to invoke a worker to compute the ``targets`` for ``source``.

        >>> scheduler = Scheduler(sources=[], targets=[])
        >>> scheduler._render_command(Ngon([1, 1, 1]), [OrbitClosure])

        """
        from itertools import chain
        from .sources.surface import Surface
        services = Services()
        services.register(Surface, lambda service: source)
        return list(chain(source.command(), *[target(services).command() for target in targets]))

    def _enqueue(self, command):
        r"""
        Run ``command`` once the load admits it.

        >>> scheduler = Scheduler(sources=[], targets=[])
        >>> scheduler._enqueue("true")

        """
        raise NotImplementedError
