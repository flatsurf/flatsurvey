r"""
Abstract interface to report progress and results of computations.

EXAMPLES::

    >>> from flatsurvey.reporting import Log
    >>> Reporter in Log.mro()
    True

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
from typing import TypeVar, overload

T = TypeVar("T")


class Reporter:
    r"""
    Base class for something that can log progress and results of computations.

    EXAMPLES::

        >>> from flatsurvey.reporting import Log
        >>> log = Log(output="-")
        >>> isinstance(log, Reporter)
        True

    """

    def log(self, source, message, **kwargs):
        r"""
        Write ``message`` emitted by ``source`` to this log.

        Most implementations will not implement this and simply ignore such messages.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log({Surface: surface}, output="-")
            >>> log.log(source=surface, message="Hello World", additional_data=1337)
            [Ngon([1, 1, 1])] [Ngon] Hello World (additional_data: 1337)

        """
        del source
        del message
        del kwargs

    async def result(self, source, result, **kwargs):
        r"""
        Report a computation's ``result`` from ``source``.

        Implementations should override this message to actually do something with the result.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> import asyncio
            >>> from flatsurvey.reporting import Log
            >>> log = Log({Surface: surface}, output="-")
            >>> report = log.result(source=surface, result="result", additional_data=1337)
            >>> asyncio.run(report)
            [Ngon([1, 1, 1])] [Ngon] result (additional_data: 1337)

        """
        del source
        del result
        del kwargs

    def progress(
        self,
        source,
        count=None,
        what=None,
        total=None,
        message=None,
    ):
        r"""
        Report that ``source`` has made some progress.

        Most implementations will not implement this and simply ignore such messages.

        EXAMPLES::

            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))

            >>> from flatsurvey.reporting import Log
            >>> log = Log({Surface: surface}, output="-")
            >>> log.progress(source=surface, what="progress", count=13, total=37)
            [Ngon([1, 1, 1])] [Ngon] progress: 13/37

        """
        del source
        del count
        del what
        del total
        del message

    def flush(self):
        r"""
        Make sure that any output has been flushed.

        Most implementation will not need to implement this.

        EXAMPLES::

            >>> from flatsurvey.reporting import Log
            >>> log = Log(output="-")
            >>> log.flush()

        """

    def _simplify_object(self, value):
        r"""
        Return the argument in a way that the report can render out.

        EXAMPLES::

            >>> from flatsurvey.reporting import Json
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))
            >>> log = Json({Surface: surface})

        Rewrites SageMath integers as Python integers::

            >>> from sage.all import ZZ

            >>> simplified = log._simplify(ZZ(1))
            >>> simplified
            1
            >>> type(simplified)
            <class 'int'>

        Rewrites SageMath rationals as Python fractions::

            >>> from sage.all import QQ

            >>> simplified = log._simplify(QQ(1/2))
            >>> simplified
            Fraction(1, 2)

        Rewrites GMP integers as Python integers::

            >>> from gmpxxyy import mpz

            >>> simplified = log._simplify(mpz(1))
            >>> simplified
            1
            >>> type(simplified)
            <class 'int'>

        Rewrites GMP rationals as Python fractions::

            >>> from gmpxxyy import mpq

            >>> simplified = log._simplify(mpq(1, 2))
            >>> simplified
            Fraction(1, 2)

        This method can be further customized by implementing
        :meth:`_simplify_unknown`.

        """
        import gmpxxyy
        from sage.all import QQ, ZZ

        if isinstance(value, type(ZZ())):
            return int(value)

        if isinstance(value, gmpxxyy.mpz):
            return int(str(value))

        if isinstance(value, type(QQ())):
            import fractions

            return fractions.Fraction(int(value.numerator()), int(value.denominator()))

        if isinstance(value, gmpxxyy.mpq):
            import fractions

            return fractions.Fraction(
                int(str(value.get_num())), int(str(value.get_den()))
            )

        if isinstance(value, (str, int, float, type(None))):
            return value

        return self._simplify_unknown(value)

    def _simplify_unknown(self, value):
        r"""
        Return the argument in a way that the report can render out.

        Subclasses can overwrite this to provide a fallback when the other
        ``_simplify`` methods do not know what to do about this value.
        """
        raise NotImplementedError(f"cannot represent {type(value)} in this report yet")

    @overload
    def _simplify(self, value: T) -> T: ...

    @overload
    def _simplify(self, value: dict, **kwargs) -> dict: ...

    @overload
    def _simplify(self, value: list, **kwargs) -> dict: ...

    def _simplify(self, *args, **kwargs):
        r"""
        Recursively rewrite the arguments and return the resulting object.

        EXAMPLES::

            >>> from flatsurvey.reporting import Json
            >>> from flatsurvey.surfaces import Ngon, Surface
            >>> surface = Ngon((1, 1, 1))
            >>> log = Json({Surface: surface})

        Combines arguments and keyword arguments::

            >>> log._simplify(1, 2, 3, a=4, b=5)
            {'a': 4, 'b': 5, 'value': (1, 2, 3)}

        """
        if not args and not kwargs:
            raise ValueError("cannot simplify nothing")

        if len(args) == 0:
            return self._simplify(kwargs)

        if len(args) > 1:
            return self._simplify(args, **kwargs)

        value = args[0]

        if kwargs:
            ret = self._simplify(kwargs)
            value = self._simplify(value)
            if isinstance(value, dict):
                ret.update(value)
            else:
                ret["value"] = value

            return ret

        if isinstance(value, tuple):
            return tuple(self._simplify(entry) for entry in value)

        if isinstance(value, list):
            return list(self._simplify(entry) for entry in value)

        if isinstance(value, dict):
            return {
                self._simplify(key): self._simplify(v) for (key, v) in value.items()
            }

        return self._simplify_object(value)
