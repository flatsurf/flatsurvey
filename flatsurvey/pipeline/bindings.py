r"""
Utilities to create the graph of objects that are performing a survey.

.. NOTE::

    This is essentially a scaled down dependency-injection framework.
    Dependency-injection is not really a thing in the Python world. Initially,
    we were using pinject but it's discontinued and it was also even more
    confusing to work with so we rolled our own.

.. NOTE::

    The principal feature we want here from the dependency injection is that it
    lets us optionally configure aspects of the object graph (say change the
    way we search for saddle connections or just stick with the defaults).

EXAMPLES:

The fundamental object here is the :class:`Bindings`. It holds the rules to
produce the object graph to run a survey of surfaces or a survey on a single
surface. Basically, a bindings can hold for each type (or string key) a rule on
how to produce it::

    >>> from flatsurvey.pipeline import Bindings
    >>> bindings = Bindings()

The easiest rules are just constants::

    >>> class Surface():
    ...     def __repr__(self): return "surface"

    >>> bindings.define(Surface, Surface())

Whenever somebody needs a Surface, we answer with this constant::

    >>> bindings.get(Surface)
    surface

The binding values can also be types, as long as they have a static
``create`` method::

    >>> class SaddleConnections:
    ...     def __init__(self, surface):
    ...         self._surface = surface
    ...
    ...     @staticmethod
    ...     def create(bindings): return SaddleConnections(bindings.get(Surface))

    >>> bindings.define("sc", SaddleConnections)

    >>> bindings.get("sc")._surface
    surface

Note that the constant is cached, you get the identical object every single
time (in dependency injection lingo, all objects have singleton lifetime.)::

    >>> bindings.get("sc") is bindings.get("sc")
    True

When asking for a type that has not been registered with ``define``, its
``create`` is also called automatically::

    >>> bindings.get(SaddleConnections)._surface
    surface

We cannot redefine names that have been requested already::

    >>> bindings.define(SaddleConnections, SaddleConnections("..."))
    Traceback (most recent call last):
    ...
    ValueError: cannot redefine ...

However, we can explicitly "forget" values and bindings for a key (this feature
has no correspondence in classic dependency injection and is just a hack that
is convenient for our purposes.)::

    >>> bindings.forget(SaddleConnections)
    >>> bindings.define(SaddleConnections, SaddleConnections("..."))

    >>> bindings.get(SaddleConnections)._surface
    '...'

Note that this forgetting is not trying to be smart in any way. Dependent
objects are still present and the forget does not affect them.

We can also only define a variable in a certain scope::

    >>> class OrbitClosure:
    ...     def __init__(self, sc, ambient):
    ...         self._sc = sc
    ...         self._ambient = ambient
    ...
    ...     @staticmethod
    ...     def create(bindings):
    ...         with bindings.scope(OrbitClosure) as scoped:
    ...             return OrbitClosure(bindings.get(SaddleConnections), scoped.get("ambient"))
    ...

    >>> with bindings.scope(OrbitClosure) as scoped:
    ...     scoped.define("ambient", "H_6(5^2, 0^2)")

    >>> bindings.get(OrbitClosure)._ambient
    'H_6(5^2, 0^2)'

Oftentimes, you want to incrementally register a list of things under one key,
say the goals of a survey::

    >>> bindings.append(list["Goal"], OrbitClosure)
    >>> bindings.append(list["Goal"], "something else")

    >>> bindings.get(list["Goal"])
    (<flatsurvey.pipeline.bindings.OrbitClosure object at 0x...>, 'something else')

"""

# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2024-2025 Julian Rüth
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


from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import contextmanager
from typing import (
    Iterable,
    Iterator,
    Protocol,
    Type,
    cast,
    overload,
    override,
    runtime_checkable,
)

Key = str | Type


@runtime_checkable
class HasCreate[T](Protocol):
    r"""
    A type that can be created from the ``bindings``.

    EXAMPLES::

        >>> from flatsurvey.jobs import OrbitClosure
        >>> isinstance(OrbitClosure, HasCreate)
        True

    """

    @staticmethod
    def create(bindings: "Bindings") -> T: ...


class Binding[T](ABC):
    r"""
    Abstract base class for possible protocols to create values that are
    requested from a :class:`Bindings`.

    EXAMPLES::

        >>> bindings = Bindings()
        >>> binding = ConstantBinding(1337)
        >>> binding.resolve(bindings)
        1337

    ::

        >>> isinstance(binding, Binding)
        True

    """

    @overload
    @staticmethod
    def create(value: "Binding[T]") -> "Binding[T]": ...

    @overload
    @staticmethod
    def create(value: T) -> "Binding[T]": ...

    @overload
    @staticmethod
    def create(value: Type[T]) -> "Binding[T]": ...

    @staticmethod
    def create(value):
        r"""
        Factory to create a concrete Binding subclass from ``value``.

        EXAMPLES::

            >>> Binding.create(123)
            ConstantBinding(123)

            >>> Binding.create(Binding)
            TypeBinding(Binding)

        """
        if isinstance(value, Binding):
            return value

        if isinstance(value, type):
            return TypeBinding(value)

        return ConstantBinding(value)

    @abstractmethod
    def resolve(self, bindings: "Bindings") -> T:
        r"""
        Return the value of this binding in ``bindings``.

        Subclasses must implement this.

        EXAMPLES::

            >>> bindings = Bindings()
            >>> binding = ConstantBinding(1337)
            >>> binding.resolve(bindings)
            1337

        """

    def clone(self) -> "Binding[T]":
        r"""
        Return an independent copy of this binding.

        EXAMPLES::

            >>> bindings = Bindings()
            >>> binding = ConstantBinding(1337)
            >>> binding.clone()
            ConstantBinding(1337)

        """
        return self


class ConstantBinding[T](Binding[T]):
    r"""
    A constant value to be stored in a Bindings.

    EXAMPLES::

        >>> bindings = Bindings()

        >>> binding = Binding.create(123)

        >>> binding.resolve(bindings)
        123

    """

    def __init__(self, value: T):
        self._value = value

    @override
    def resolve(self, bindings: "Bindings") -> T:
        del bindings  # unused
        return self._value

    def __repr__(self):
        return f"ConstantBinding({self._value})"


class TypeBinding[T: HasCreate](Binding[T]):
    r"""
    A value that is invoking ``.create`` on a type.

    EXAMPLES::

        >>> bindings = Bindings()


        >>> class A:
        ...     @staticmethod
        ...     def create(bindings): return A()

        >>> binding = Binding.create(A)

        >>> binding.resolve(bindings)
        <flatsurvey.pipeline.bindings.A object at 0x...>

    """

    def __init__(self, type: Type[T]):
        self._type = type

    @override
    def resolve(self, bindings) -> T:
        try:
            return self._type.create(bindings)
        except Exception as e:
            raise BindingException(
                f"Cannot create instance of '{self._type.__name__}' from bindings"
            ) from e

    def __repr__(self):
        return f"TypeBinding({self._type.__name__})"


class ListBinding[T](Binding[tuple[T, ...]]):
    r"""
    A value that is an (expandable but finite) sequence of other bindings.

    EXAMPLES::

        >>> bindings = Bindings()


        >>> binding = ListBinding()
        >>> binding.append(Binding.create(1))
        >>> binding.append(Binding.create(2))

        >>> binding.resolve(bindings)
        (1, 2)

    """

    def __init__(self):
        self._value: list[Binding[T]] = []

    def append(self, binding):
        self._value.append(binding)

    @override
    def resolve(self, bindings: "Bindings") -> tuple[T, ...]:
        return tuple(binding.resolve(bindings) for binding in self._value)

    def __repr__(self):
        return f"ListBinding({self._value})"

    def clone(self):
        r"""
        Return an independent copy of this binding.

        EXAMPLES::

            >>> bindings = Bindings()


            >>> binding = ListBinding()
            >>> binding.append(Binding.create(1))

            >>> clone = binding.clone()
            >>> binding.append(Binding.create(2))

            >>> binding.resolve(bindings)
            (1, 2)
            >>> clone.resolve(bindings)
            (1,)

        """
        clone = ListBinding()
        clone._value = self._value[:]
        return clone


class Bindings:
    r"""
    Rules to create an object graph.

    EXAMPLES:

    Typically, a survey creates such a bindings to describe the general setup::

        >>> survey = Bindings()
        >>> survey.append(list["goal"], "some goal")
        >>> survey.survey("surface", ["surface0", "surface1"])

    To perform the survey, the survey is iterating over the surfaces and
    sending a patched object graph to each worker::

        >>> for bindings in survey.survey_bindings:
        ...     # would send item to an actual worker process and process it there
        ...     bindings.get("surface"), bindings.get(list["goal"])
        ('surface0', ('some goal',))
        ('surface1', ('some goal',))

    """

    def __init__(self, repr=None):
        self._values = {}
        self._bindings = {}
        self._scopes = {}
        self._survey = {}
        self._repr: str | None = repr

    @staticmethod
    def click(wrapped):
        r"""
        Decorator helper to add a bindings argument to a click command handler.

        EXAMPLES::

            >>> import click
            >>> @click.command("demo")
            ... @Bindings.click
            ... def demo(bindings):
            ...     bindings.append("goals", "demo")

            >>> from flatsurvey.test.cli import invoke_subcommand
            >>> invoke_subcommand(demo, "--help")  # doctest: +NORMALIZE_WHITESPACE
            Usage: doctest demo [OPTIONS]
            Options:
              --help  Show this message and exit.

        """
        from functools import wraps

        @wraps(wrapped)
        def command(*args, **kwargs):
            def wrapper(bindings: Bindings):
                wrapped(bindings, *args, **kwargs)

            return wrapper

        return command

    @contextmanager
    def scope(self, scope: str | Type):
        r"""
        Return the scoped bindings for ``scope``.

        A scope is a completely isolated namespace for the object graph.
        Bindings in the scoped context are not visible outside the scope and
        vice versa.

        EXAMPLES::

            >>> bindings = Bindings()
            >>> with bindings.scope("local") as scoped:
            ...     scoped.define("variable", 1337)

            >>> bindings.get("variable")
            Traceback (most recent call last):
            ...
            flatsurvey.pipeline.bindings.BindingException: Cannot resolve 'variable' from bindings

            >>> with bindings.scope("local") as scoped:
            ...     scoped.get("variable")
            1337

        """
        if scope not in self._scopes:
            self._scopes[scope] = Bindings()

        try:
            yield self._scopes[scope]
        except Exception as e:
            raise Exception(f"Error while in binding scope '{scope}'") from e

    def append(self, key: Key, value):
        r"""
        Append ``value`` to the list binding for ``key``.

        EXAMPLES::

            >>> bindings = Bindings()
            >>> bindings.append(list["goal"], "OrbitClosure")

            >>> bindings.get(list["goal"])
            ('OrbitClosure',)

        """
        from typing import get_origin

        if get_origin(key) != list:
            raise ValueError("key must be a list[?]")

        if key not in self._bindings:
            self._bindings[key] = ListBinding()

        self._bindings[key].append(Binding.create(value))

    def survey(self, key: Key, values: Iterable[object]):
        r"""
        Expand the objects to survey by the ``values``.

        If ``survey`` is called for the same key with multiple values, they
        will be iterated in :meth:`survey_bindings` in a roundrobin manner.

        If ``survey`` is called with different keys, then
        :meth:`survey_bindings` will iterate over their product in a zig-zag.

        EXAMPLES::

            >>> bindings = Bindings()
            >>> bindings.survey("surface", ["square torus", "golden L"])
            >>> bindings.survey("surface", ["double pentagon", "octagon"])
            >>> bindings.survey("coefficients", ["e-antic", "exact-real"])

            >>> list(bindings.survey_bindings)  # doctest: +NORMALIZE_WHITESPACE
            [Bindings(survey surface=square torus,coefficients=e-antic),
             Bindings(survey surface=double pentagon,coefficients=e-antic),
             Bindings(survey surface=square torus,coefficients=exact-real),
             Bindings(survey surface=golden L,coefficients=e-antic),
             Bindings(survey surface=double pentagon,coefficients=exact-real),
             Bindings(survey surface=octagon,coefficients=e-antic),
             Bindings(survey surface=golden L,coefficients=exact-real),
             Bindings(survey surface=octagon,coefficients=exact-real)]

        """
        if key not in self._survey:
            self._survey[key] = []
        self._survey[key].append(values)

    @property
    def survey_bindings(self) -> Iterator["Bindings"]:
        r"""
        Return a binding for each object registered to survey in
        :meth:`survey`.

        Typically, this returns an infinite iterator of bindings.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngons, Surface

            >>> bindings = Bindings()
            >>> bindings.survey(Surface, Ngons(vertices=3, min=0, limit=None, count=None, literature="include", family=None, filter=None))
            >>> bindings.survey(Surface, Ngons(vertices=4, min=0, limit=None, count=None, literature="include", family=None, filter=None))
            >>> survey_bindings = bindings.survey_bindings

            >>> next(survey_bindings)
            Bindings(survey <class 'flatsurvey.surfaces.surface.Surface'>=Ngon([1, 1, 1]))
            >>> next(survey_bindings)
            Bindings(survey <class 'flatsurvey.surfaces.surface.Surface'>=Ngon([1, 1, 1, 1]))
            >>> next(survey_bindings)
            Bindings(survey <class 'flatsurvey.surfaces.surface.Surface'>=Ngon([1, 1, 2]))
            >>> next(survey_bindings)
            Bindings(survey <class 'flatsurvey.surfaces.surface.Surface'>=Ngon([1, 1, 1, 2]))

        """
        from more_itertools import roundrobin
        from sympy.utilities.iterables import iproduct

        sources = {key: roundrobin(*values) for key, values in self._survey.items()}

        for values in iproduct(*sources.values()):
            keys = sources.keys()
            bindings = self.clone(
                repr=f"Bindings(survey {','.join(f'{key}={value}' for key, value in zip(keys, values))})"
            )
            configuration = {}
            for key, value in zip(keys, values):
                configuration[key] = value
                bindings.define(key, value)

            bindings.define(configuration=configuration)

            yield bindings

    @overload
    def define(self, key: Key, value: object, /): ...

    @overload
    def define(self, /, **value): ...

    def define(self, key: Key | None = None, value=None, /, **values):
        r"""
        Set the rule to create ``key`` to ``value``.

        Alternatively, key/value pairs can be given as keyword arguments.

        EXAMPLES::

            >>> bindings = Bindings()
            >>> bindings.define("key", "value")
            >>> bindings.get("key")
            'value'

        ::

            >>> bindings = Bindings()
            >>> bindings.define(key="value")
            >>> bindings.get("key")
            'value'

        """
        if key is not None:
            if key in self._bindings:
                raise ValueError(f"cannot redefine {key}")
            if key in self._values:
                raise ValueError(f"cannot redefine {key} which already has a value")

            self._bindings[key] = Binding.create(value)

        for key, value in values.items():
            self.define(key, value)

    @overload
    def set(self, key: Key, value: object, /): ...

    @overload
    def set(self, /, **value): ...

    def set(self, key: Key | None = None, value=None, /, **values):
        r"""
        Set the value of ``key`` to the actual ``value``.

        Alternatively, key/value pairs can be given as keyword arguments.

        For constant values, this is essentially like ``define``, however,
        :meth:`forget` will forget about the values set with ``set``.

        The values must be actual values and not types or bindings.

        EXAMPLES::

            >>> bindings = Bindings()
            >>> bindings.set("key", "value")
            >>> bindings.get("key")
            'value'

        ::

            >>> bindings = Bindings()
            >>> bindings.set(key="value")
            >>> bindings.get("key")
            'value'

        """
        if key is not None:
            if key in self._values:
                raise ValueError(f"cannot reset {key}")

            self._values[key] = value

        for key, value in values.items():
            self.set(key, value)

    def get[T](self, key: Key, default: T | Callable[[], T] | None = None) -> T:
        r"""
        Resolve the ``key`` in this bindings.

        If no ``key`` has been registered in this scope, return ``default`` if
        set.

        EXAMPLES::

            >>> bindings = Bindings()
            >>> bindings.set(key="value")
            >>> bindings.get("key")
            'value'

        """
        try:
            if key not in self._values:
                if key not in self._bindings:
                    if default is None:
                        if isinstance(key, type):
                            self.define(key, key)
                        else:
                            raise Exception(
                                f"cannot resolve {key} and no default given"
                            )
                    else:
                        if callable(default):
                            default = cast(T, default())

                        self.set(key, default)
                        return default

                self.set(key, self._bindings[key].resolve(self))

            return self._values[key]
        except Exception as e:
            raise BindingException(f"Cannot resolve '{key}' from bindings") from e

    def __repr__(self):
        return self._repr or super().__repr__()

    def clone(self, repr=None):
        r"""
        Return a copy of the bindings.

        The copy has the same bindings but forgets about the concrete values
        that these bindings produced if any.

        EXAMPLES::

            >>> from flatsurvey.pipeline import Bindings
            >>> bindings = Bindings()

            >>> class Surface():
            ...     def __repr__(self): return "surface"
            ...     @staticmethod
            ...     def create(bindings): return Surface()

            >>> bindings.get(Surface) is bindings.get(Surface)
            True

            >>> clone = bindings.clone()
            >>> bindings.get(Surface) is clone.get(Surface)
            False

        """
        clone = Bindings(repr=repr)
        clone._bindings = {
            key: binding.clone() for key, binding in self._bindings.items()
        }
        clone._scopes = {scope: child.clone() for scope, child in self._scopes.items()}
        if clone._survey:
            raise NotImplementedError("cannot clone a survey binding")
        return clone

    def forget(self, key: Key):
        r"""
        Forget bindings and concrete values for ``key``.

        EXAMPLES::

            >>> bindings = Bindings()
            >>> bindings.define(key="value")
            >>> bindings.get("key")
            'value'

            >>> bindings.forget("key")
            >>> bindings.set(key='other')
            >>> bindings.get("key")
            'other'

        """
        if key in self._bindings:
            del self._bindings[key]

        if key in self._values:
            del self._values[key]


class BindingException(Exception):
    r"""
    Generic exception that is thrown when a binding could not be resolved.

    EXAMPLES::

        >>> bindings = Bindings()
        >>> bindings.get(list)
        Traceback (most recent call last):
        ...
        flatsurvey.pipeline.bindings.BindingException: Cannot resolve ...

    """

    pass
