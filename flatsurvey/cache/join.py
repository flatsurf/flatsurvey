r"""
Aggregate cache files.

Combines JSON files that are produced by the
:class:`flatsurvey.reporting.json.Json` reporter into files grouped by subject,
i.e., type of result.

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.cache.maintenance import cli
    >>> invoke(cli, "join", "--help")  # doctest: +NORMALIZE_WHITESPACE
    Usage: cli join [OPTIONS] [JSONS]...
      Aggregates JSON files into one file for each type of result.
    Options:
      --outdir PATH  a directory to write the output files to  [required]
      --help         Show this message and exit.

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

from pathlib import Path

import click

from flatsurvey.pipeline import Bindings, Goal
from flatsurvey.ui import Command


class Join(Goal, Command):
    r"""
    Aggregates JSON files into one file for each type of result.

    INPUT:

    - ``jsons`` -- a list of paths of existing JSON files.

    - ``outdir`` -- the output directory to write the JSON files to.

    EXAMPLES::

        >>> Join(jsons=[], outdir=Path("/tmp/"))
        join

    """

    def __init__(self, jsons: list[Path], outdir: Path):
        super().__init__()

        self._jsons = jsons
        self._outdir = outdir

    @staticmethod
    @click.command(name="join", help=__doc__.split("INPUT")[0])  # type: ignore
    @click.argument("jsons", nargs=-1, type=click.Path(exists=True, path_type=Path))
    @click.option(
        "--outdir",
        type=click.Path(path_type=Path),
        required=True,
        help="a directory to write the output files to",
    )
    @Bindings.click
    def click(bindings: Bindings, jsons, outdir):
        r"""
        Parse command line options into ``bindings``.

        TESTS::

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(Join.click, "--outdir=/tmp")

        """
        bindings.append(list[Goal], Join)
        with bindings.scope(Join) as scoped:
            scoped.define(jsons=jsons, outdir=outdir)

    @staticmethod
    def create(bindings: Bindings):
        r"""
        Return a ``Join`` instance from the configuration registered in
        ``bindings``.

        TESTS::

            >>> from flatsurvey.pipeline import Bindings
            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> bindings = Bindings()
            >>> invoke_subcommand(Join.click, "--outdir=/tmp", bindings=bindings)
            >>> Join.create(bindings)
            join

        """
        with bindings.scope(Join) as scoped:
            return Join(jsons=scoped.get("jsons"), outdir=scoped.get("outdir"))

    async def resolve(self):
        r"""
        Perform this maintenance task, i.e., read the JSON files and repackage
        them into subject specific JSON files.

        EXAMPLES::

            >>> from pathlib import Path
            >>> from tempfile import TemporaryDirectory
            >>> import asyncio

            >>> with TemporaryDirectory() as tmpdir:
            ...     tmpdir = Path(tmpdir)
            ...     with open(tmpdir / "a.json", "w") as json: _ = json.write('{"subject": [{"result": true}]}')
            ...     with open(tmpdir / "b.json", "w") as json: _ = json.write('{"subject": [{"result": false}]}')
            ...     join = Join(jsons=[tmpdir / "a.json", tmpdir / "b.json"], outdir=tmpdir)
            ...     asyncio.run(join.resolve())
            ...     with open(tmpdir / "subject.json") as json: print(json.read())
            True
            {
              "subject": [
                {
                  "result": true
                },
                {
                  "result": false
                }
              ]
            }

        Note that this is idempotent. Processing the output through the join
        again leaves the files unmodified.

        """
        from flatsurvey.cache import Cache

        subjects = Cache.load(self._jsons)

        self._outdir.mkdir(parents=True, exist_ok=True)

        for subject, values in subjects.items():
            with open(self._outdir / f"{subject}.json", "w") as output:
                import json

                json.dump({subject: values}, output, indent=2)

        return True


__test__ = {
    # doctests of click do not run unless explicitly mentioned here due to the click decorator.
    "Join.click": Join.click.__doc__,
}
