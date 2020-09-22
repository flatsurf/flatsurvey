import sys
import click

from pinject import copy_args_to_internal_fields

from ..util.click.group import GroupedCommand

from .report import Reporter

class Log(Reporter):
    @copy_args_to_internal_fields
    def __init__(self, surface, stream=sys.stdout):
        pass

    def log(self, message, **kwargs):
        if kwargs:
            message = "%s (%s)"%(message, kwargs)
        self._stream.write("%s\n"%(message,))
        self._stream.flush()

    def progress(self, source, unit, count, total=None):
        self.log("[%s] [%s] %s: %s/%s"%(self._surface, source, unit, count, total or '?'))

    def command(self):
        if self._stream is sys.stdout: output = []
        else: output = ["--output", self._stream.name]
        return ["log"] + output


@click.command(name="log", cls=GroupedCommand, group="Reports")
@click.option("--output", type=click.File("w"), default=None)
def log(output):
    class Configured(Log):
        def __init__(self, surface):
            stream = output or open("%s.log"%(surface._name,), "w")
            super().__init__(surface, stream=stream)
    return Configured
