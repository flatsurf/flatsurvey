import click

import pdb

from ..sources import sources
from ..targets import targets
from ..services import Services
from ..sources.surface import Surface

@click.group(chain=True)
def worker(): pass

for kind in [sources, targets]:
    for command in kind:
        worker.add_command(command)

@worker.resultcallback()
def process(commands):
    source = None
    targets = []

    for command in commands:
        if isinstance(command, Surface):
            if source is not None:
                raise ValueError("cannot process more than one source")
            source = command
        else:
            targets.append(command)

    services = Services()
    services.register(Surface, lambda services: source)
    Worker(services, targets).start()

class Worker:
    def __init__(self, services, targets):
        self.services = services
        self.targets = []

        for target in targets:
            self.targets.append(self.services.get(target))

    def start(self):
        for target in self.targets:
            try:
                target.resolve()
            except:
                pdb.post_mortem()

if __name__ == "__main__": worker()
