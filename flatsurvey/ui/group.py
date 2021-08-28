r"""
Helpers to organize commands and options in groups.

Note that this was heavily inspired by discussion in
https://github.com/pallets/click/issues/373.

"""
#*********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2021 Julian Rüth
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
#*********************************************************************

import click

from collections import defaultdict


class CommandWithGroups(click.Group):
    r"""
    Base class for commands that want to use the other utilities in this
    module.
    """
    def format_options(self, ctx, formatter):
        # Write options in sorted groups
        options = defaultdict(list)
        for param in self.get_params(ctx):
            if param.get_help_record(ctx):
                group = 'Options'
                if isinstance(param, GroupedOption): group = param.group
                options[group].append(param.get_help_record(ctx))
        for group in sorted(options.keys()):
            with formatter.section(group):
                formatter.write_dl(sorted(options[group]))

        self.format_commands(ctx, formatter)

    def format_commands(self, ctx, formatter):
        # Write commands in sorted groups
        commands = defaultdict(list)
        for command in self.list_commands(ctx):
            cmd = self.get_command(ctx, command)
            group = 'Commands'
            if hasattr(cmd, "group"): group = cmd.group
            commands[group].append((command, cmd.get_short_help_str()))
        for group in sorted(commands.keys()):
            with formatter.section(group):
                formatter.write_dl(sorted(commands[group]))


class GroupedCommand(click.Command):
    r"""
    Base class for subcommands to group subcommands by topic.
    """
    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)

    def get_short_help_str(self, limit=None):
        return super().get_short_help_str(limit=1024)


class GroupedOption(click.Option):
    r"""
    Base class for options to group options by topic.
    """
    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)
