r"""
Entrypoint to run surveys.
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

import click

from .sources import generators
from .targets import targets
from .services import Services

@click.group(chain=True)
def survey():
    r"""
    Main command, runs a survey; specific survey sources and targets are
    registered automatically as subcommands.

    >>> from click.testing import CliRunner
    >>> CliRunner().invoke(survey)

    """

for kind in [generators, targets]:
    for command in kind:
        survey.add_command(command)

@survey.resultcallback()
def process(commands):
    sources = []
    targets = []
    for command in commands:
        from collections.abc import Iterable
        if isinstance(command, Iterable):
            sources.append(command)
        else:
            targets.append(command)

    Scheduler(sources, targets).start()


class Scheduler:
    def __init__(self, sources, targets):
        self.sources = sources
        self.targets = targets

    def start(self):
        for source in self.sources:
            for item in source:
                self._work(item)

    def _work(self, source):
        command = self._render_command(source)
        self._run(command)

    def _render_command(self, source):
        from itertools import chain
        from .sources.surface import Surface
        services = Services()
        services.register(Surface, lambda service: source)
        return list(chain(source.command(), *[target(services).command() for target in self.targets]))

    def _run(self, command):
        print(command)


if __name__ == "__main__": survey()
