r"""
Helpers to organize commands and options in groups.

Note that this was heavily inspired by discussion in
https://github.com/pallets/click/issues/373.

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

from collections import defaultdict

import click


class CommandWithGroups(click.Group):
    r"""
    Base class for commands that want to display grouped subcommands.

    EXAMPLES::

        >>> from flatsurvey.survey import survey
        >>> isinstance(survey, CommandWithGroups)
        True

    """

    def format_commands(self, ctx, formatter):
        # Write commands in sorted groups
        commands = defaultdict(list)
        for command in self.list_commands(ctx):
            cmd = self.get_command(ctx, command)
            assert cmd is not None
            group = "Commands"
            if hasattr(cmd, "group"):
                group = cmd.group  # pyright: ignore
            commands[group].append((command, cmd))
        for group in sorted(commands.keys()):
            # Formula copied from the base class implementation
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands[group])
            with formatter.section(group):
                formatter.write_dl(
                    [
                        (command, cmd.get_short_help_str(limit=limit))
                        for (command, cmd) in sorted(commands[group])
                    ]
                )


class GroupedCommand(click.Command):
    r"""
    Base class for subcommands to appear in a topic in a
    :class:`CommandWithGroups` documentation.

    EXAMPLES::

        >>> @click.group(cls=CommandWithGroups)
        ... def command(): pass

        >>> @click.command(name="subcommand", group="GROUP", cls=GroupedCommand)
        ... def subcommand(): pass

        >>> command.add_command(subcommand)

        >>> from flatsurvey.test.cli import invoke
        >>> invoke(command, "--help")  # doctest: +NORMALIZE_WHITESPACE
        Usage: command [OPTIONS] COMMAND [ARGS]...
        Options:
          --help  Show this message and exit.
        GROUP:
          subcommand

    """

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop("group", None)
        super().__init__(*args, **kwargs)
