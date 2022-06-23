r"""
Access cached results from previous runs.

Currently, the only cache we support is a plain-text database stored in .json
files and some accompanying Python pickles. It would be fairly trivial to
change that and allow for other similar systems as well (and we at some point
supported a GraphQL backend but it turned out to be impractical.)

EXAMPLES::

    >>> from flatsurvey.test.cli import invoke
    >>> from flatsurvey.worker.__main__ import worker
    >>> invoke(worker, "local-cache", "--help") # doctest: +NORMALIZE_WHITESPACE
    Usage: worker local-cache [OPTIONS]
      A cache of previous results stored in local JSON files.
    Options:
      -j, --json PATH  JSON files to read cached data from or a directory to read recursively
      --help           Show this message and exit.

"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020-2022 Julian Rüth
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

import click
from pinject import copy_args_to_internal_fields

from flatsurvey.pipeline.util import PartialBindingSpec
from flatsurvey.ui.group import GroupedCommand
from flatsurvey.command import Command


class Cache(Command):
    r"""
    A cache of previous results stored in local JSON files.

    EXAMPLES::

        >>> from flatsurvey.cache.pickles import Pickles
        >>> Cache(pickles=None, jsons=())
        local-cache

    """

    @copy_args_to_internal_fields
    def __init__(
        self,
        pickles,
        report,
        jsons=(),
    ):
        def load(file):
            try:
                import orjson
                return orjson.loads(file.read())
            except ModuleNotFoundError:
                import json
                return json.loads(file.read())

        self._cache = {}

        with report.progress(self, what="files", count=0, total=len(jsons), activity="loading cache"):
            for json in jsons:
                parsed = load(json)

                for section, results in parsed.items():
                    self._cache.setdefault(section, []).extend(results)

                report.progress(self, advance=1, message=f"processed {json.name}")

            report.progress(self, message="done")

            self._sources = [("CACHE", "DEFAULTS", "PICKLE")]
            self._defaults = [{}]
            self._shas = {}

    @classmethod
    @click.command(
        name="local-cache",
        cls=GroupedCommand,
        group="Cache",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option(
        "--json",
        "-j",
        metavar="PATH",
        multiple=True,
        type=str,
        help="JSON files to read cached data from or a directory to read recursively",
    )
    def click(json):
        jsons = []

        for j in json:
            import os.path
            if os.path.isdir(j):
                for root, dirs, files in os.walk(j):
                    for f in files:
                        if f.endswith(".json"):
                            jsons.append(open(os.path.join(root, f), "rb"))
            else:
                jsons.append(open(j, "rb"))

        return {
            "bindings": Cache.bindings(jsons)
        }

    def command(self):
        return ["local-cache"] + [f"--json={json.name}" for json in self._jsons]

    @classmethod
    def bindings(cls, jsons):
        return [PartialBindingSpec(Cache, name="cache", scope="SHARED")(jsons=jsons)]

    def deform(self, deformation):
        return {"bindings": Cache.bindings()}

    def sources(self, *sources):
        r"""
        TODO: Document and test.
        """
        if len(sources) == 0:
            return self._sources[-1]

        from contextlib import contextmanager

        @contextmanager
        def with_sources():
            self._sources.append(sources)
            try:
                yield None
            finally:
                assert self._sources[-1] is sources
                self._sources.pop()

        return with_sources()

    def unpickle(self, pickle, kind):
        r"""
        Return the ``pickle`` identified by its SHA256 by loading it from the
        pickle storage.

        The storage might have multiple buckets. The bucket for ``kind`` is
        queried, or all buckets if ``None``.
        """
        if self._pickles is None:
            raise NotImplementedError("cannot unpickle since no pickle source has been passed to this cache")

        return self._pickles.unpickle(pickle, kind)

    def defaults(self, defaults=None):
        r"""
        Get or set the defaults used for keys that are missing from a node.

        EXAMPLES:

        When no parameters are provided, the defaults are returned::

            >>> from flatsurvey.cache.pickles import Pickles
            >>> from io import StringIO
            >>> cache = Cache(jsons=(StringIO('{"A": [{}]}'),), pickles=None)
            >>> cache.defaults()
            {}

        Otherwise, a context is returned for whose lifetime the defaults are replaced::

            >>> with cache.defaults({"type": "B"}):
            ...     cache.defaults()
            {'type': 'B'}

        ::

            >>> with cache.defaults({"type": "B"}):
            ...     cache.get("A")[0].type
            'B'

        """
        if defaults is None:
            return self._defaults[-1]

        from contextlib import contextmanager

        @contextmanager
        def with_defaults():
            self._defaults.append(defaults)
            try:
                yield None
            finally:
                assert self._defaults[-1] is defaults
                self._defaults.pop()

        return with_defaults()

    def get(self, section, predicate=None, single=None):
        r"""
        Return the results for ``section`` that satisfy ``predicate``.

        EXAMPLES:

        Cached results are automatically requested by a goal when
        :meth:`Goal._consume_cache` which calls this method.

        However, the cache can also be queried manually. Let's suppose that we
        have a cache from previous runs::

        # TODO: Create an issue that these pickles should be more compact.

            >>> from flatsurvey.cache.pickles import Pickles
            >>> from io import StringIO
            >>> json = '{"orbit-closure": [{"dense": true, "dimension": 7, "surface": {"type": "Ngon", "angles": [1, 2, 4], "pickle": "a1b54e02ade464584920abcbfd07faaa71afac1d5b455a56d5cf790ccf5528da"}}, {"surface": {"type": "Ngon", "angles": [3, 4, 13],'\
            ...        '"pickle": "93a35e3ae58f6c981ee0e40f5b14c44026095cbd1a655efb438ce75b4ce0f961"}, "dimension": 4, "pickle": "2d42b17964db400f6d73c09b6014c9612cafc3512781e4ebd6477354aee56d70"}]}'
            >>> pickles = [
            ... b'\x80\x04\x95\x00\x0e\x00\x00\x00\x00\x00\x00\x8c\x1dflatsurvey.jobs.orbit_closure\x94\x8c\x0cOrbitClosure\x94\x93\x94)\x81\x94}\x94(\x8c\x08_surface\x94\x8c\x19flatsurvey.surfaces.ngons\x94\x8c\x04Ngon\x94\x93\x94]\x94(K\x03K\x04K\re'
            ... b'\x8c\x07e-antic\x94\x8c,sage.rings.number_field.number_field_element\x94\x8c\x1bNumberFieldElement_absolute\x94\x93\x94\x8c\x16sage.structure.factory\x94\x8c\x18generic_factory_unpickle\x94\x93\x94(h\x0e\x8c\rlookup_global\x94\x93\x94'
            ... b'\x8c9sage.rings.number_field.number_field.NumberField_version2\x94\x85\x94R\x94K\tK\x06\x86\x94(\x8c\x19sage.rings.rational_field\x94\x8c\rRationalField\x94\x93\x94)R\x94\x8c/sage.rings.polynomial.polynomial_rational_flint\x94\x8c\x19'
            ... b'Polynomial_rational_flint\x94\x93\x94(\x8c1sage.rings.polynomial.polynomial_ring_constructor\x94\x8c\x17unpickle_PolynomialRing\x94\x93\x94(h\x1a\x8c\x01x\x94\x85\x94N\x89t\x94R\x94]\x94(\x8c\x13sage.rings.rational\x94\x8c\rmake_rati'
            ... b'onal\x94\x93\x94\x8c\x015\x94\x85\x94R\x94h(\x8c\x010\x94\x85\x94R\x94h(\x8c\x02-5\x94\x85\x94R\x94h(h,\x85\x94R\x94h(\x8c\x011\x94\x85\x94R\x94e\x89\x89t\x94R\x94\x8c\x02c0\x94\x85\x94\x8c\x1csage.structure.dynamic_class\x94\x8c\rdy'
            ... b'namic_class\x94\x93\x94(\x8c AlgebraicRealField_with_category\x94\x8c\x10sage.rings.qqbar\x94\x8c\x12AlgebraicRealField\x94\x93\x94\x8c\x08builtins\x94\x8c\x07getattr\x94\x93\x94\x8c$sage.structure.unique_representation\x94\x8c\x08un'
            ... b'reduce\x94\x93\x94\x8c\x18sage.categories.category\x94\x8c\x0cJoinCategory\x94\x93\x94\x8c\x0esage.misc.call\x94\x8c\x0bcall_method\x94\x93\x94hMhMhMhMhMhMhMhMhG\x8c*sage.categories.magmas_and_additive_magmas\x94\x8c\x17MagmasAndAddi'
            ... b'tiveMagmas\x94\x93\x94)}\x94\x87\x94R\x94\x8c\x0b_with_axiom\x94\x8c\x0cDistributive\x94\x87\x94R\x94hT\x8c\x13AdditiveAssociative\x94\x87\x94R\x94hT\x8c\x13AdditiveCommutative\x94\x87\x94R\x94hT\x8c\x0eAdditiveUnital\x94\x87\x94R\x94'
            ... b'hT\x8c\x0bAssociative\x94\x87\x94R\x94hT\x8c\x0fAdditiveInverse\x94\x87\x94R\x94hT\x8c\x06Unital\x94\x87\x94R\x94hT\x8c\x08Division\x94\x87\x94R\x94hT\x8c\x0bCommutative\x94\x87\x94R\x94hMhG\x8c\x18sage.categories.sets_cat\x94\x8c\x04'
            ... b'Sets\x94\x93\x94)}\x94\x87\x94R\x94hT\x8c\x08Infinite\x94\x87\x94R\x94\x86\x94\x85\x94}\x94\x87\x94R\x94\x8c\x0cparent_class\x94\x86\x94R\x94\x86\x94NNhAt\x94R\x94)R\x94h?\x8c\rAlgebraicReal\x94\x93\x94h?\x8c\x12ANExtensionElement\x94'
            ... b'\x93\x94h?\x8c\x12AlgebraicGenerator\x94\x93\x94h\x10(h\x15h\x16(h\x1ah\x1d(h (h\x1a\x8c\x01y\x94\x85\x94N\x89t\x94R\x94]\x94(h(h4\x85\x94R\x94h(h,\x85\x94R\x94h(\x8c\x02-c\x94\x85\x94R\x94h(h,\x85\x94R\x94h(\x8c\x01j\x94\x85\x94R\x94'
            ... b'h(h,\x85\x94R\x94h(\x8c\x02-8\x94\x85\x94R\x94h(h,\x85\x94R\x94h(h4\x85\x94R\x94e\x89\x89t\x94R\x94\x8c\x01a\x94\x85\x94Nh\xa7N\x89Nt\x94}\x94\x8c\x05check\x94\x89st\x94R\x94h?\x8c\x06ANRoot\x94\x93\x94h?\x8c\x1aAlgebraicPolynomialTr'
            ... b'acker\x94\x93\x94h\x1d(h\x8e]\x94(h(h4\x85\x94R\x94h(h,\x85\x94R\x94h(\x8c\x02-c\x94\x85\x94R\x94h(h,\x85\x94R\x94h(h\x99\x85\x94R\x94h(h,\x85\x94R\x94h(\x8c\x02-8\x94\x85\x94R\x94h(h,\x85\x94R\x94h(h4\x85\x94R\x94e\x89\x89t\x94R\x94'
            ... b'\x85\x94R\x94\x8c\x14sage.rings.real_mpfi\x94\x8c+__create__RealIntervalFieldElement_version1\x94\x93\x94h\xcb\x8c$__create__RealIntervalField_version0\x94\x93\x94K\x80\x89\x86\x94R\x94\x8c\x14sage.rings.real_mpfr\x94\x8c\x1d__create'
            ... b'__RealNumber_version0\x94\x93\x94h\xd2\x8c\x1c__create__RealField_version0\x94\x93\x94K\x80\x89\x8c\x04RNDU\x94\x87\x94R\x94\x8c\x1e1.v6p4ignu8msq5hn483j7cijmco@0\x94K \x87\x94R\x94h\xd4h\xd6K\x80\x89\x8c\x04RNDD\x94\x87\x94R\x94\x8c'
            ... b'\x1e1.v6p4ignu8msq5hn483j7cijm9o@0\x94K \x87\x94R\x94\x87\x94R\x94K\x01\x87\x94R\x94\x86\x94R\x94h\rh\xadh\x1d(h (h\x1ah!\x85\x94N\x89t\x94R\x94]\x94(h(\x8c\x02-2\x94\x85\x94R\x94h(h,\x85\x94R\x94h(h4\x85\x94R\x94e\x89\x89t\x94R\x94\x86'
            ... b'\x94R\x94\x86\x94R\x94\x85\x94R\x94\x86\x94\x8c\x05c_{0}\x94N\x89Nt\x94}\x94h\xab\x88st\x94R\x94h\x1d(h\xeb]\x94h(\x8c\x0210\x94\x85\x94R\x94a\x89\x89t\x94R\x94\x86\x94R\x94h\rj\x01\x01\x00\x00h\x1d(h\xeb]\x94(h(\x8c\x0210\x94\x85\x94'
            ... b'R\x94h(\x8c\x0440/5\x94\x85\x94R\x94h(\x8c\x05-1g/5\x94\x85\x94R\x94h(\x8c\x05-10/5\x94\x85\x94R\x94e\x89\x89t\x94R\x94\x86\x94R\x94h\rj\x01\x01\x00\x00h\x1d(h\xeb]\x94(h(\x8c\x0250\x94\x85\x94R\x94h(\x8c\x0240\x94\x85\x94R\x94h(\x8c'
            ... b'\x03-1g\x94\x85\x94R\x94h(\x8c\x03-10\x94\x85\x94R\x94e\x89\x89t\x94R\x94\x86\x94R\x94\x87\x94\x87\x94R\x94\x8c\x07_report\x94\x8c\x1bflatsurvey.reporting.report\x94\x8c\x06Report\x94\x93\x94)\x81\x94}\x94(\x8c\n_reporters\x94]\x94\x8c'
            ... b'\x07_ignore\x94]\x94ub\x8c\x14_flow_decompositions\x94\x8c"flatsurvey.jobs.flow_decomposition\x94\x8c\x12FlowDecompositions\x94\x93\x94)\x81\x94}\x94(h\x05j.\x01\x00\x00j/\x01\x00\x00j2\x01\x00\x00)\x81\x94}\x94(j5\x01\x00\x00]\x94j7'
            ... b'\x01\x00\x00]\x94ub\x8c\x1f_saddle_connection_orientations\x94\x8c.flatsurvey.jobs.saddle_connection_orientations\x94\x8c\x1cSaddleConnectionOrientations\x94\x93\x94)\x81\x94}\x94(\x8c\x13_saddle_connections\x94\x8c"flatsurvey.jobs.s'
            ... b'addle_connections\x94\x8c\x11SaddleConnections\x94\x93\x94)\x81\x94}\x94(h\x05j.\x01\x00\x00\x8c\x06_limit\x94N\x8c\x06_bound\x94N\x8c\n_consumers\x94\x8f\x94(jG\x01\x00\x00\x90\x8c\x08_current\x94N\x8c\n_exhausted\x94\x89\x8c\x0c_co'
            ... b'nnections\x94NubjQ\x01\x00\x00\x8f\x94(j=\x01\x00\x00\x90jS\x01\x00\x00NjT\x01\x00\x00\x89\x8c\n_producers\x94]\x94jM\x01\x00\x00a\x8c\t_resolved\x94\x88j/\x01\x00\x00j2\x01\x00\x00)\x81\x94}\x94(j5\x01\x00\x00]\x94j7\x01\x00\x00]\x94'
            ... b'ub\x8c\t_produced\x94\x89\x8c\x05_seen\x94NubjO\x01\x00\x00M\x00\x01jQ\x01\x00\x00\x8f\x94(h\x03\x90jS\x01\x00\x00NjT\x01\x00\x00\x89jW\x01\x00\x00]\x94jG\x01\x00\x00ajY\x01\x00\x00\x88j^\x01\x00\x00\x89ubjI\x01\x00\x00jM\x01\x00\x00'
            ... b'\x8c\x06_cache\x94\x8c\x16flatsurvey.cache.cache\x94\x8c\x05Cache\x94\x93\x94)\x81\x94}\x94(\x8c\x08_pickles\x94N\x8c\x06_jsons\x94)\x8c\x08_results\x94}\x94\x8c\x08_sources\x94]\x94\x8c\x05CACHE\x94\x8c\x06PICKLE\x94\x8c\x08DEFAULTS'
            ... b'\x94\x87\x94a\x8c\t_defaults\x94]\x94}\x94aubjO\x01\x00\x00K \x8c\x0b_expansions\x94K\x04\x8c\x07_deform\x94\x89\x8c\x0b_cache_only\x94\x89jW\x01\x00\x00]\x94j=\x01\x00\x00ajY\x01\x00\x00\x88\x8c\x1b_cylinders_without_increase\x94K\x00'
            ... b'\x8c\x1a_directions_with_cylinders\x94K\x00\x8c\x0b_directions\x94K\x00\x8c\x15_expansions_performed\x94K\x00\x8c\t_deformed\x94\x88\x8c\x0c_lower_bound\x94\x8c!cppyythonizations.pickling.cereal\x94\x8c\x14unpickle_from_cereal\x94\x93'
            ... b'\x94\x8c\x12cppyy.gbl.flatsurf\x94\x8c\x05Bound\x94\x93\x94}\x94\x8c\x06square\x94h,s]\x94\x8c\x13flatsurf/cereal.hpp\x94a\x87\x94R\x94\x8c\x0c_upper_bound\x94j\x81\x01\x00\x00j\x84\x01\x00\x00}\x94\x8c\x06square\x94h,sj\x87\x01\x00\x00'
            ... b'\x87\x94R\x94ub.',
            ... b'\x80\x03cflatsurvey.surfaces.ngons\nNgon\nq\x00]q\x01(csage.rings.integer\nmake_integer\nq\x02X\x01\x00\x00\x001q\x03\x85q\x04Rq\x05h\x02X\x01\x00\x00\x002q\x06\x85q\x07Rq\x08h\x02X\x01\x00\x00\x004q\t\x85q\nRq\x0beX\x07\x00\x00\x00e'
            ... b'-anticq\x0ccsage.rings.number_field.number_field_element\nNumberFieldElement_absolute\nq\rcsage.structure.factory\ngeneric_factory_unpickle\nq\x0e(csage.structure.factory\nlookup_global\nq\x0fX9\x00\x00\x00sage.rings.number_field.num'
            ... b'ber_field.NumberField_version2q\x10\x85q\x11Rq\x12K\tK\x02\x86q\x13(csage.rings.rational_field\nRationalField\nq\x14)Rq\x15csage.rings.polynomial.polynomial_rational_flint\nPolynomial_rational_flint\nq\x16(csage.rings.polynomial.poly'
            ... b'nomial_ring_constructor\nunpickle_PolynomialRing\nq\x17(h\x15X\x01\x00\x00\x00xq\x18\x85q\x19N\x89tq\x1aRq\x1b]q\x1c(csage.rings.rational\nmake_rational\nq\x1dX\x02\x00\x00\x00-7q\x1e\x85q\x1fRq h\x1dX\x01\x00\x00\x000q!\x85q"Rq#h\x1d'
            ... b'X\x01\x00\x00\x00eq$\x85q%Rq&h\x1dh!\x85q\'Rq(h\x1dX\x02\x00\x00\x00-7q)\x85q*Rq+h\x1dh!\x85q,Rq-h\x1dh\x03\x85q.Rq/e\x89\x89tq0Rq1X\x01\x00\x00\x00cq2\x85q3csage.structure.dynamic_class\ndynamic_class\nq4(X \x00\x00\x00AlgebraicReal'
            ... b'Field_with_categoryq5csage.rings.qqbar\nAlgebraicRealField\nq6cbuiltins\ngetattr\nq7csage.structure.unique_representation\nunreduce\nq8csage.categories.category\nJoinCategory\nq9csage.misc.call\ncall_method\nq:h:h:h:h:h:h:h:h:h8csage'
            ... b'.categories.magmas_and_additive_magmas\nMagmasAndAdditiveMagmas\nq;)}q<\x87q=Rq>X\x0b\x00\x00\x00_with_axiomq?X\x0c\x00\x00\x00Distributiveq@\x87qARqBh?X\x13\x00\x00\x00AdditiveAssociativeqC\x87qDRqEh?X\x13\x00\x00\x00AdditiveCommuta'
            ... b'tiveqF\x87qGRqHh?X\x0e\x00\x00\x00AdditiveUnitalqI\x87qJRqKh?X\x0b\x00\x00\x00AssociativeqL\x87qMRqNh?X\x0f\x00\x00\x00AdditiveInverseqO\x87qPRqQh?X\x06\x00\x00\x00UnitalqR\x87qSRqTh?X\x08\x00\x00\x00DivisionqU\x87qVRqWh?X\x0b\x00\x00'
            ... b'\x00CommutativeqX\x87qYRqZh:h8csage.categories.sets_cat\nSets\nq[)}q\\\x87q]Rq^h?X\x08\x00\x00\x00Infiniteq_\x87q`Rqa\x86qb\x85qc}qd\x87qeRqfX\x0c\x00\x00\x00parent_classqg\x86qhRqi\x86qjNNh6tqkRql)Rqmcsage.rings.qqbar\nAlgebraicReal'
            ... b'\nqncsage.rings.qqbar\nANExtensionElement\nqocsage.rings.qqbar\nAlgebraicGenerator\nqph\x0e(h\x12h\x13(h\x15h\x16(h\x17(h\x15X\x01\x00\x00\x00yqq\x85qrN\x89tqsRqt]qu(h\x1dX\x02\x00\x00\x00-7qv\x85qwRqxh\x1dh!\x85qyRqzh\x1dh$\x85q{Rq|'
            ... b'h\x1dh!\x85q}Rq~h\x1dX\x02\x00\x00\x00-7q\x7f\x85q\x80Rq\x81h\x1dh!\x85q\x82Rq\x83h\x1dh\x03\x85q\x84Rq\x85e\x89\x89tq\x86Rq\x87X\x01\x00\x00\x00aq\x88\x85q\x89Nh\x88N\x89Ntq\x8a}q\x8bX\x05\x00\x00\x00checkq\x8c\x89stq\x8dRq\x8ecsage'
            ... b'.rings.qqbar\nANRoot\nq\x8fcsage.rings.qqbar\nAlgebraicPolynomialTracker\nq\x90h\x16(ht]q\x91(h\x1dX\x02\x00\x00\x00-7q\x92\x85q\x93Rq\x94h\x1dh!\x85q\x95Rq\x96h\x1dh$\x85q\x97Rq\x98h\x1dh!\x85q\x99Rq\x9ah\x1dX\x02\x00\x00\x00-7q\x9b'
            ... b'\x85q\x9cRq\x9dh\x1dh!\x85q\x9eRq\x9fh\x1dh\x03\x85q\xa0Rq\xa1e\x89\x89tq\xa2Rq\xa3\x85q\xa4Rq\xa5csage.rings.real_mpfi\n__create__RealIntervalFieldElement_version1\nq\xa6csage.rings.real_mpfi\n__create__RealIntervalField_version0\nq'
            ... b'\xa7K@\x89\x86q\xa8Rq\xa9csage.rings.real_mpfr\n__create__RealNumber_version0\nq\xaacsage.rings.real_mpfr\n__create__RealField_version0\nq\xabK@\x89X\x04\x00\x00\x00RNDUq\xac\x87q\xadRq\xaeX\x11\x00\x00\x001.ucks0lceiq73k@0q\xafK \x87'
            ... b'q\xb0Rq\xb1h\xaah\xabK@\x89X\x04\x00\x00\x00RNDDq\xb2\x87q\xb3Rq\xb4X\x11\x00\x00\x001.ucks0lceiq73g@0q\xb5K \x87q\xb6Rq\xb7\x87q\xb8Rq\xb9K\x01\x87q\xbaRq\xbb\x86q\xbcRq\xbdh\rh\x8eh\x16(h\x17(h\x15h\x18\x85q\xbeN\x89tq\xbfRq\xc0]q\xc1'
            ... b'(h\x1dh!\x85q\xc2Rq\xc3h\x1dh\x03\x85q\xc4Rq\xc5e\x89\x89tq\xc6Rq\xc7\x86q\xc8Rq\xc9\x86q\xcaRq\xcb\x85q\xccRq\xcd\x86q\xceh2N\x89Ntq\xcf}q\xd0h\x8c\x88stq\xd1Rq\xd2h\x16(h\xc0]q\xd3h\x1dX\x02\x00\x00\x0010q\xd4\x85q\xd5Rq\xd6a\x89\x89'
            ... b'tq\xd7Rq\xd8\x86q\xd9Rq\xdah\rh\xd2h\x16(h\xc0]q\xdb(h\x1dh!\x85q\xdcRq\xddh\x1dX\x05\x00\x00\x00-40/7q\xde\x85q\xdfRq\xe0h\x1dh!\x85q\xe1Rq\xe2h\x1dX\x04\x00\x00\x0030/7q\xe3\x85q\xe4Rq\xe5h\x1dh!\x85q\xe6Rq\xe7h\x1dX\x04\x00\x00\x00'
            ... b'-g/7q\xe8\x85q\xe9Rq\xeae\x89\x89tq\xebRq\xec\x86q\xedRq\xeeh\rh\xd2h\x16(h\xc0]q\xef(h\x1dh!\x85q\xf0Rq\xf1h\x1dX\x05\x00\x00\x00-40/7q\xf2\x85q\xf3Rq\xf4h\x1dh!\x85q\xf5Rq\xf6h\x1dX\x04\x00\x00\x0030/7q\xf7\x85q\xf8Rq\xf9h\x1dh!\x85'
            ... b'q\xfaRq\xfbh\x1dX\x04\x00\x00\x00-g/7q\xfc\x85q\xfdRq\xfee\x89\x89tq\xffRr\x00\x01\x00\x00\x86r\x01\x01\x00\x00Rr\x02\x01\x00\x00\x87r\x03\x01\x00\x00\x87r\x04\x01\x00\x00Rr\x05\x01\x00\x00.',
            ... b'\x80\x03cflatsurvey.surfaces.ngons\nNgon\nq\x00]q\x01(csage.rings.integer\nmake_integer\nq\x02X\x01\x00\x00\x003q\x03\x85q\x04Rq\x05h\x02X\x01\x00\x00\x004q\x06\x85q\x07Rq\x08h\x02X\x01\x00\x00\x00dq\t\x85q\nRq\x0beX\x07\x00\x00\x00e'
            ... b'-anticq\x0ccsage.modules.free_module_element\nmake_FreeModuleElement_generic_dense_v1\nq\r(csage.structure.factory\ngeneric_factory_unpickle\nq\x0e(csage.structure.factory\nlookup_global\nq\x0fX\n\x00\x00\x00FreeModuleq\x10\x85q\x11R'
            ... b'q\x12K\tK\x02\x86q\x13(h\x0e(h\x0fX9\x00\x00\x00sage.rings.number_field.number_field.NumberField_version2q\x14\x85q\x15Rq\x16K\tK\x02\x86q\x17(csage.rings.rational_field\nRationalField\nq\x18)Rq\x19csage.rings.polynomial.polynomial_r'
            ... b'ational_flint\nPolynomial_rational_flint\nq\x1a(csage.rings.polynomial.polynomial_ring_constructor\nunpickle_PolynomialRing\nq\x1b(h\x19X\x01\x00\x00\x00xq\x1c\x85q\x1dN\x89tq\x1eRq\x1f]q (csage.rings.rational\nmake_rational\nq!X\x01'
            ... b'\x00\x00\x005q"\x85q#Rq$h!X\x01\x00\x00\x000q%\x85q&Rq\'h!X\x02\x00\x00\x00-5q(\x85q)Rq*h!h%\x85q+Rq,h!X\x01\x00\x00\x001q-\x85q.Rq/e\x89\x89tq0Rq1X\x02\x00\x00\x00c0q2\x85q3csage.structure.dynamic_class\ndynamic_class\nq4(X \x00\x00'
            ... b'\x00AlgebraicRealField_with_categoryq5csage.rings.qqbar\nAlgebraicRealField\nq6cbuiltins\ngetattr\nq7csage.structure.unique_representation\nunreduce\nq8csage.categories.category\nJoinCategory\nq9csage.misc.call\ncall_method\nq:h:h:h:'
            ... b'h:h:h:h:h:h8csage.categories.magmas_and_additive_magmas\nMagmasAndAdditiveMagmas\nq;)}q<\x87q=Rq>X\x0b\x00\x00\x00_with_axiomq?X\x0c\x00\x00\x00Distributiveq@\x87qARqBh?X\x13\x00\x00\x00AdditiveAssociativeqC\x87qDRqEh?X\x13\x00\x00\x00'
            ... b'AdditiveCommutativeqF\x87qGRqHh?X\x0e\x00\x00\x00AdditiveUnitalqI\x87qJRqKh?X\x0b\x00\x00\x00AssociativeqL\x87qMRqNh?X\x0f\x00\x00\x00AdditiveInverseqO\x87qPRqQh?X\x06\x00\x00\x00UnitalqR\x87qSRqTh?X\x08\x00\x00\x00DivisionqU\x87qVRq'
            ... b'Wh?X\x0b\x00\x00\x00CommutativeqX\x87qYRqZh:h8csage.categories.sets_cat\nSets\nq[)}q\\\x87q]Rq^h?X\x08\x00\x00\x00Infiniteq_\x87q`Rqa\x86qb\x85qc}qd\x87qeRqfX\x0c\x00\x00\x00parent_classqg\x86qhRqi\x86qjNNh6tqkRql)Rqmcsage.rings.qqba'
            ... b'r\nAlgebraicReal\nqncsage.rings.qqbar\nANExtensionElement\nqocsage.rings.qqbar\nAlgebraicGenerator\nqph\x0e(h\x16h\x17(h\x19h\x1a(h\x1b(h\x19X\x01\x00\x00\x00yqq\x85qrN\x89tqsRqt]qu(h!h-\x85qvRqwh!h%\x85qxRqyh!X\x02\x00\x00\x00-cqz\x85'
            ... b'q{Rq|h!h%\x85q}Rq~h!X\x01\x00\x00\x00jq\x7f\x85q\x80Rq\x81h!h%\x85q\x82Rq\x83h!X\x02\x00\x00\x00-8q\x84\x85q\x85Rq\x86h!h%\x85q\x87Rq\x88h!h-\x85q\x89Rq\x8ae\x89\x89tq\x8bRq\x8cX\x01\x00\x00\x00aq\x8d\x85q\x8eNh\x8dN\x89Ntq\x8f}q\x90'
            ... b'X\x05\x00\x00\x00checkq\x91\x89stq\x92Rq\x93csage.rings.qqbar\nANRoot\nq\x94csage.rings.qqbar\nAlgebraicPolynomialTracker\nq\x95h\x1a(ht]q\x96(h!h-\x85q\x97Rq\x98h!h%\x85q\x99Rq\x9ah!X\x02\x00\x00\x00-cq\x9b\x85q\x9cRq\x9dh!h%\x85q\x9e'
            ... b'Rq\x9fh!h\x7f\x85q\xa0Rq\xa1h!h%\x85q\xa2Rq\xa3h!X\x02\x00\x00\x00-8q\xa4\x85q\xa5Rq\xa6h!h%\x85q\xa7Rq\xa8h!h-\x85q\xa9Rq\xaae\x89\x89tq\xabRq\xac\x85q\xadRq\xaecsage.rings.real_mpfi\n__create__RealIntervalFieldElement_version1\nq\xaf'
            ... b'csage.rings.real_mpfi\n__create__RealIntervalField_version0\nq\xb0K@\x89\x86q\xb1Rq\xb2csage.rings.real_mpfr\n__create__RealNumber_version0\nq\xb3csage.rings.real_mpfr\n__create__RealField_version0\nq\xb4K@\x89X\x04\x00\x00\x00RNDUq\xb5'
            ... b'\x87q\xb6Rq\xb7X\x11\x00\x00\x001.v6p4ignu8msq8@0q\xb8K \x87q\xb9Rq\xbah\xb3h\xb4K@\x89X\x04\x00\x00\x00RNDDq\xbb\x87q\xbcRq\xbdX\x11\x00\x00\x001.v6p4ignu8msq4@0q\xbeK \x87q\xbfRq\xc0\x87q\xc1Rq\xc2K\x01\x87q\xc3Rq\xc4\x86q\xc5Rq\xc6'
            ... b'csage.rings.number_field.number_field_element\nNumberFieldElement_absolute\nq\xc7h\x93h\x1a(h\x1b(h\x19h\x1c\x85q\xc8N\x89tq\xc9Rq\xca]q\xcb(h!X\x02\x00\x00\x00-2q\xcc\x85q\xcdRq\xceh!h%\x85q\xcfRq\xd0h!h-\x85q\xd1Rq\xd2e\x89\x89tq\xd3'
            ... b'Rq\xd4\x86q\xd5Rq\xd6\x86q\xd7Rq\xd8\x85q\xd9Rq\xda\x86q\xdbX\x05\x00\x00\x00c_{0}q\xdcN\x89Ntq\xdd}q\xdeh\x91\x88stq\xdfRq\xe0K\x03\x89Ntq\xe1}q\xe2tq\xe3Rq\xe4]q\xe5(h\xc7h\xe0h\x1a(h\xca]q\xe6h!h-\x85q\xe7Rq\xe8a\x89\x89tq\xe9Rq\xea'
            ... b'\x86q\xebRq\xech\xc7h\xe0h\x1a(h\xca]q\xed(h!h-\x85q\xeeRq\xefh!X\x03\x00\x00\x004/5q\xf0\x85q\xf1Rq\xf2h!X\x04\x00\x00\x00-3/aq\xf3\x85q\xf4Rq\xf5h!X\x04\x00\x00\x00-1/5q\xf6\x85q\xf7Rq\xf8e\x89\x89tq\xf9Rq\xfa\x86q\xfbRq\xfch\xc7h\xe0'
            ... b'h\x1a(h\xca]q\xfd(h!h"\x85q\xfeRq\xffh!h\x06\x85r\x00\x01\x00\x00Rr\x01\x01\x00\x00h!X\x04\x00\x00\x00-3/2r\x02\x01\x00\x00\x85r\x03\x01\x00\x00Rr\x04\x01\x00\x00h!X\x02\x00\x00\x00-1r\x05\x01\x00\x00\x85r\x06\x01\x00\x00Rr\x07\x01\x00'
            ... b'\x00e\x89\x89tr\x08\x01\x00\x00Rr\t\x01\x00\x00\x86r\n\x01\x00\x00Rr\x0b\x01\x00\x00eK\x03\x88tr\x0c\x01\x00\x00Rr\r\x01\x00\x00\x87r\x0e\x01\x00\x00Rr\x0f\x01\x00\x00.'
            ... ]
            >>> cache = Cache(jsons=[StringIO(json)], pickles=Pickles(pickles))

        Then we can query all cached results for a goal::

            >>> from flatsurvey.jobs import OrbitClosure
            >>> cache.get(OrbitClosure)
            [{'dense': True, 'dimension': 7, 'surface': {'type': 'Ngon', 'angles': [1, 2, 4], 'pickle': '...'}}, {'surface': {'type': 'Ngon', 'angles': [3, 4, 13], ...}, ...}]

        We can filter the results further by specifying a predicate::

            >>> len(cache.get(OrbitClosure, predicate=lambda entry: entry.dense is not True)) == 1
            True

        Or, if we only want results for a specific surface (the ``cache=cache``
        parameter is optional but speeds up searches a lot)::

            >>> from flatsurvey.surfaces import Ngon
            >>> surface = Ngon((1, 2, 4))
            >>> cache.get(OrbitClosure, predicate=surface.cache_predicate(exact=False, cache=cache))
            [{'dense': True, 'dimension': 7, 'surface': {'type': 'Ngon', 'angles': [1, 2, 4], 'pickle': '...'}}]

        The above returns the results for any ngon with such angles. To only
        accept results for surfaces that are exactly the same, we can use the
        ``exact`` keyword; however this is not implemented yet::

            >>> cache.get(OrbitClosure, predicate=surface.cache_predicate(exact=True))
            Traceback (most recent call last):
            ...
            NotImplementedError: exact filtering is not supported yet

        We can also only look at results for surfaces with certain properties::

            >>> cache.get(OrbitClosure, predicate=lambda entry: entry.dense is not True)
            [{'surface': {'type': 'Ngon', 'angles': [3, 4, 13], 'pickle': '93a35e3ae58f6c981ee0e40f5b14c44026095cbd1a655efb438ce75b4ce0f961'}, 'dimension': 4, 'pickle': '2d42b17964db400f6d73c09b6014c9612cafc3512781e4ebd6477354aee56d70'}]


        Note that the above operation could be expensive because it needs to
        restore the pickle of the orbit closure where "dense" was not included
        in the cache. Instead, we can tell the cache to ignore pickles for
        "dense" and assume a default value instead::

            >>> with cache.defaults({"dense": None}):
            ...     with cache.sources("CACHE", "DEFAULTS"):
            ...         cache.get(OrbitClosure, predicate=lambda entry: entry.dense is not True)
            [{'surface': {'type': 'Ngon', 'angles': [3, 4, 13], 'pickle': '93a35e3ae58f6c981ee0e40f5b14c44026095cbd1a655efb438ce75b4ce0f961'}, 'dimension': 4, 'pickle': '2d42b17964db400f6d73c09b6014c9612cafc3512781e4ebd6477354aee56d70'}]

        We can also use more elaborate queries on the underlying objects,
        again, these could be very costly::

            >>> cache.get(OrbitClosure, predicate=lambda entry: entry.dimension != entry.surface.orbit_closure_dimension_upper_bound)
            [{'surface': {'type': 'Ngon', 'angles': [3, 4, 13], 'pickle': '93a35e3ae58f6c981ee0e40f5b14c44026095cbd1a655efb438ce75b4ce0f961'}, 'dimension': 4, 'pickle': '2d42b17964db400f6d73c09b6014c9612cafc3512781e4ebd6477354aee56d70'}]

        """
        if isinstance(section, (type, Command)):
            section = section.name()

        if predicate is None:
            def predicate(node):
                return True

        if isinstance(predicate, str):
            if single is None:
                single = True

            results = [self._from_sha(section, predicate)]
        else:
            if single is None:
                single = False

            results = []

            for entry in self._cache.get(section, []):
                node = self.make(entry, section)

                if not predicate(node):
                    continue

                results.append(node)

        if single:
            if len(results) > 1:
                raise ValueError(f"expected at most one result but found {len(results)}")

            if len(results) == 0:
                raise KeyError

            return results[0]

        return results

    def _from_sha(self, section, sha):
        if section not in self._shas:
            self._shas[section] = {entry["pickle"]: entry for entry in self._cache[section]}

        return self.make(self._shas[section][sha], section)

    def make(self, value, name, kind=None):
        if kind is None:
            if isinstance(value, dict) and "type" in value:
                kind = value["type"]
            else:
                kind = name

        if value is None:
            return None

        if isinstance(value, list):
            if name.endswith('s'):
                name = name[:-1]
            else:
                name = None
            return [self.make(v, name=name) for v in value]

        if isinstance(value, str) and name in ["surface"]:
            from flatsurvey.cache.node import ReferenceNode
            return ReferenceNode(value, "surface", cache=self)

        if isinstance(value, (bool, int, str)):
            return value

        from flatsurvey.cache.node import Node
        return Node(value, cache=self, kind=kind)
