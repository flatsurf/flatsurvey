r"""
Helpers for click CLI testing.

Click's own CliRunner is quite cumbersome to work with in some simple test
scenarios so we wrap it in more convenient ways here.

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

def invoke(command, *args):
    r"""
    Invoke the click ``command`` with the given list of string arguments.

    >>> @click.command()
    ... def hello(): print("Hello World")
    >>> invoke(hello)
    Hello World

    >>> @click.command()
    ... def fails(): raise Exception("expected error")
    >>> invoke(fails)
    Traceback (most recent call last):
    ...
    Exception: expected error

    """
    from click.testing import CliRunner
    invocation = CliRunner().invoke(command, args, catch_exceptions=False)
    output = invocation.output.strip()
    if output: print(output)
