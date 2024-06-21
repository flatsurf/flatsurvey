r"""
Convenience methods for the dependency injection framework pinject.
"""
# *********************************************************************
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
# *********************************************************************

import inspect

import pinject.bindings


def ListBindingSpec(name, sequence, scope=None):
    r"""
    Return a BindingSpec that provides the instances of the types in
    ``sequence`` as a list.

    EXAMPLES::

        >>> class SomeDependency: pass
        >>> class AnotherDependency: pass
        >>> binding = ListBindingSpec("list", [SomeDependency, AnotherDependency])
        >>> inspect.signature(binding.provide_list)
        <Signature (some_dependency, another_dependency)>

    """
    from types import FunctionType

    args = [
        pinject.bindings.default_get_arg_names_from_class_name(typ.__name__)[0]
        for typ in sequence
    ]
    provider = (
        f"def provide_{name}(self, {', '.join(args)}): return [{', '.join(args)}]"
    )
    provider = FunctionType(
        compile(provider, "<string>", "exec").co_consts[0], {}, f"provide_{name}"
    )
    provider.__module__ = "__main__"
    binding = type(
        f"{name}ListBinding",
        (pinject.BindingSpec,),
        {f"provide_{name}": provider, "__repr__": lambda self: f"{name}->{sequence}"},
    )()
    binding.name = name
    binding.scope = scope or "DEFAULT"

    return binding


def PartialBindingSpec(prototype, name=None, scope=None):
    r"""
    A decorator to wrap the callable ``prototype`` and creates a BindingSpec to
    provide it with some of its arguments bound.

    This is essentially like functools.partial. However, the generated provide_
    method does not use *args and **kwargs in its actual signature but the original
    argument names. The injection mechanism of pinject relies on these names to
    be present in the signature.

    EXAMPLES::

        >>> class AaaBee:
        ...     def __init__(self, a, b): pass
        >>> binding = PartialBindingSpec(AaaBee)(a=1)
        >>> inspect.signature(binding.provide_aaa_bee)
        <Signature (b)>

    We can also explicitly rebind under a different name::

        >>> binding = PartialBindingSpec(AaaBee, name="bee")(a=1)
        >>> inspect.signature(binding.provide_bee)
        <Signature (b)>

    """
    from types import FunctionType

    name = (
        name
        or pinject.bindings.default_get_arg_names_from_class_name(prototype.__name__)[0]
    )
    signature = inspect.signature(prototype)

    def wrap(**kwargs):
        injected = [
            param.name
            for param in signature.parameters.values()
            if param.name not in kwargs and param.default is inspect._empty
        ]
        args = [f"{arg}={arg}" for arg in injected + list(kwargs.keys())]
        provider = f"def provide_{name}(self, {', '.join(injected)}): return prototype({', '.join(args)})"
        provider = FunctionType(
            compile(provider, "<string>", "exec").co_consts[0],
            {**kwargs, "prototype": prototype},
            f"provide_{name}",
        )
        provider.__module__ = "__main__"
        binding = type(
            f"Partial{prototype.__name__}Binding",
            (pinject.BindingSpec,),
            {
                f"provide_{name}": provider,
                "__repr__": lambda self: f"{name} binding to {prototype.__name__}",
            },
        )()
        binding.name = name
        binding.scope = scope or "DEFAULT"
        return binding

    return wrap


def FactoryBindingSpec(name, prototype, scope=None):
    r"""
    Return a BindingSpec that calls ``prototype`` as a provider for ``name``.

    EXAMPLES::

        >>> def create(dependency): return 1337
        >>> binding = FactoryBindingSpec("object", create)
        >>> inspect.signature(binding.provide_object)
        <Signature (dependency)>

    """
    from types import FunctionType

    signature = inspect.signature(prototype)
    args = [param for param in signature.parameters.keys()]
    provider = f"def provide_{name}(self, {', '.join(args)}): return prototype({', '.join(args)})"
    provider = FunctionType(
        compile(provider, "<string>", "exec").co_consts[0],
        {"prototype": prototype},
        f"provide_{name}",
    )
    provider.__module__ = "__main__"
    binding = type(
        f"{name}FactoryBinding",
        (pinject.BindingSpec,),
        {f"provide_{name}": provider, "__repr__": lambda self: f"{name}->{prototype}"},
    )()
    binding.name = name
    binding.scope = scope or "DEFAULT"

    return binding


def provide(name, objects):
    src = compile(
        f"""
class Provider:
    def __init__(self, { name }): self.value = { name }
    """,
        "<string>",
        "exec",
    )
    scope = {}
    exec(src, scope)
    provider = scope["Provider"]
    # pinject expects a module on the __init__ (probably for no good reason)
    provider.__init__.__module__ = provide.__module__
    return objects.provide(provider).value
