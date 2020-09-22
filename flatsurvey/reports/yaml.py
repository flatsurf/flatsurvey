import sys
import click

from pinject import copy_args_to_internal_fields

from ..util.click.group import GroupedCommand

from .report import Reporter

class Pickle:
    def __init__(self, raw):
        self._raw = raw

    @classmethod
    def to_yaml(cls, representer, data):
        import base64
        return representer.represent_scalar(u'tag:yaml.org,2002:binary', base64.encodebytes(data._raw).decode('ascii'), style='')

    @classmethod
    def from_yaml(self, constructor, obj):
        raise NotImplementedError


class Yaml(Reporter):
    @copy_args_to_internal_fields
    def __init__(self, surface, stream=sys.stdout):
        self._data = { 'surface': surface }

        from ruamel.yaml import YAML
        self._yaml = YAML()
        self._yaml.width = 2**16
        self._yaml.representer.default_flow_style = None
        self._yaml.representer.add_representer(None, Yaml._represent_undefined)
        self._yaml.register_class(type(self._data['surface']))
        self._yaml.register_class(Pickle)

    @classmethod
    def _represent_undefined(cls, representer, data):
        import pickle
        return representer.represent_data({
            "pickle": Pickle(pickle.dumps(data)),
            "repr": repr(data),
        })

    def _render(self, *args, **kwargs):
        if len(args) == 0:
            return self._render(kwargs)
        
        if len(args) > 1:
            return self._render(args, **kwargs)

        value = args[0]
        if not kwargs:
            from sage.all import ZZ
            if type(value) is type(ZZ()):
                value = int(value)
            if hasattr(type(value), 'to_yaml'):
                self._yaml.representer.add_representer(type(value), type(value).to_yaml)
            return value

        value = self._render(value)
        ret = self._render(kwargs)
        if isinstance(value, dict):
            ret.update(value)
        else:
            ret['value'] = value
        return ret
    
    def update(self, source, result, **kwargs):
        self._data[source.key()] = self._render(result, **kwargs)

    def partial(self, source, result, **kwargs):
        self._data.get(source.key(), []).append(self._render(result, **kwargs))

    def flush(self):
        self._yaml.dump(self._data, self._stream)
        self._stream.flush()

    def command(self):
        if self._stream is sys.stdout: output = []
        else: output = ["--output", self._stream.name]
        return ["yaml"] + output


@click.command(name="yaml", cls=GroupedCommand, group="Reports")
@click.option("--output", type=click.File("w"), default=None)
def yaml(output):
    class Configured(Yaml):
        def __init__(self, surface):
            stream = output or open("%s.yaml"%(surface._name,), "w")
            super().__init__(surface, stream=stream)
    return Configured
