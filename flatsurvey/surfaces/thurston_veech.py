r"""
Translation surfaces coming from Thurston-Veech constructions

EXAMPLES::

    >>> from flatsurvey.surfaces.thurston_veech import ThurstonVeech
    >>> ThurstonVeech((1,0,2), (0,2,1), [1,1], [1,1]).surface()
    TranslationSurface built from 3 polygons
"""
# *********************************************************************
#  This file is part of flatsurvey.
#
#        Copyright (C) 2020 Vincent Delecroix
#        Copyright (C) 2021 Julian Rüth
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
from sage.all import QQ, IntegerVectors, cached_method, libgap

from flatsurvey.surfaces.surface import Surface
from flatsurvey.ui.group import GroupedCommand


class ThurstonVeech(Surface):
    r"""
    Thurston-Veech construction

    EXAMPLES::

        >>> from flatsurvey.surfaces.thurston_veech import ThurstonVeech
        >>> TV = ThurstonVeech((1,0,2), (0,2,1), (1,1), (1,1))
        >>> TV
        ThurstonVeech((1, 0, 2), (0, 2, 1), (1, 1), (1, 1))
        >>> S = TV.surface()
        >>> S
        TranslationSurface built from 3 polygons
        >>> S.base_ring()
        Number Field in a with defining polynomial x^2 - x - 1 with a = 1.618033988749895?
    """

    def __init__(self, hp, vp, hm, vm):
        if len(hp) != len(vp):
            raise ValueError(
                "hp and vp must be zero based permutations of the same size"
            )
        self.hp = hp
        self.vp = vp
        if not all(hm) or not all(vm):
            raise ValueError("hm and vm must be positive vectors")
        self.hm = hm
        self.vm = vm

        # TODO: Move this to the super() invocation instead.
        self._eliminate_marked_points = True

    @property
    def orbit_closure_dimension_upper_bound(self):
        o = self.origami()

        if self._surface().base_ring() is QQ:
            # arithmetic Teichmueller curve
            return 2

        # NOTE: in order to do something more sensible, we need to have access to an up to
        # date list of GL(2,R)-orbit closures and possibly implement some ad-hoc detection
        # for Thurston-Veech construction.
        # see https://github.com/flatsurf/sage-flatsurf/issues/133

        return o.stratum().dimension()

    def __repr__(self):
        return "ThurstonVeech({}, {}, {}, {})".format(
            self.hp, self.vp, self.hm, self.vm
        )

    def reference(self):
        r"""
        EXAMPLES::

            >>> from flatsurvey.surfaces.thurston_veech import ThurstonVeech

            >>> hp = (1, 0, 3, 2, 5, 4, 7, 6)
            >>> vp = (7, 2, 1, 4, 3, 6, 5, 0)
            >>> ThurstonVeech(hp, vp, (1,1,1,1), (1,1,1,1)).reference()
            'An origami'
            >>> ThurstonVeech(hp, vp, (1,2,1,2), (2,3,2,5)).reference() is None
            True
        """
        # TODO: known exotic loci. See #13.
        if self._surface().base_ring() is QQ:
            return "An origami"

        # TODO: some of the quotient might come from something else than
        # automorphisms... Something needs to be done for each block of
        # the monodromy. See #13.
        A = self.orientable_automorphisms()
        if not libgap.IsTrivial(A):
            oo = self.origami().quotient(A)
            return "Translation covering of {}".format(oo.stratum())

    @cached_method
    def origami(self):
        return self._thurston_veech()._o

    @cached_method
    def _thurston_veech(self):
        from flatsurf.geometry.thurston_veech import ThurstonVeech

        # NOTE: the ThurstonVeech constructor should support the as_tuple keyword
        # of surface-dynamics Origami that allows permutation to starts with 0.
        # see https://github.com/flatsurf/sage-flatsurf/issues/133
        hp = [i + 1 for i in self.hp]
        vp = [i + 1 for i in self.vp]
        return ThurstonVeech(hp, vp)

    @cached_method
    def _surface(self):
        return self._thurston_veech()(self.hm, self.vm)

    @cached_method
    def orientable_automorphisms(self):
        r"""
        EXAMPLES::

            >>> from flatsurvey.surfaces.thurston_veech import ThurstonVeech

            >>> hp = (1,0,3,2)
            >>> vp = (0,2,1,3)
            >>> TV = ThurstonVeech(hp, vp, (1,1), (1,1,1))
            >>> TV.orientable_automorphisms()
            Group([ (1,4)(2,3) ])

            >>> TV = ThurstonVeech(hp, vp, (1,2), (1,1,1))
            >>> TV.orientable_automorphisms()
            Group(())

            >>> TV = ThurstonVeech(hp, vp, (1,1), (1,2,1))
            >>> TV.orientable_automorphisms()
            Group([ (1,4)(2,3) ])

            >>> TV = ThurstonVeech(hp, vp, (1,1), (1,1,2))
            >>> TV.orientable_automorphisms()
            Group(())
        """
        o = self.origami()
        n = o.nb_squares()

        M = libgap.Group([o.r(), o.u()])
        Sn = libgap.SymmetricGroup(n)
        A = libgap.Centralizer(Sn, M)
        if A.Size() == 1:
            return A

        # 1. compute action of the automorphisms on horiz / vert cylinders
        from surface_dynamics.misc.permutation import perm_dense_cycles

        hcyls, hdeg = perm_dense_cycles(o.r_tuple(), n)
        vcyls, vdeg = perm_dense_cycles(o.u_tuple(), n)
        hreps = [None] * len(self.hm)
        vreps = [None] * len(self.vm)
        for i in range(n):
            j = hcyls[i]
            if hreps[j] is None:
                hreps[j] = i
            j = vcyls[i]
            if vreps[j] is None:
                vreps[j] = i

        hgens = []  # induced action on horizontal cylinders
        vgens = []  # induced action on vertical cylinders
        for p in libgap.GeneratorsOfGroup(A):
            hgens.append(
                libgap.PermList(
                    [hcyls[(hreps[i] + 1) ** p - 1] + 1 for i in range(len(self.hm))]
                )
            )
            vgens.append(
                libgap.PermList(
                    [vcyls[(vreps[i] + 1) ** p - 1] + 1 for i in range(len(self.vm))]
                )
            )
        hP = libgap.Group(hgens)
        vP = libgap.Group(vgens)
        hH = libgap.GroupHomomorphismByImages(A, hP, hgens)
        vH = libgap.GroupHomomorphismByImages(A, vP, vgens)

        # 2. compute the subgroup that stabilizes hm / vm
        hd = defaultdict(list)
        for i, j in enumerate(self.hm):
            hd[j].append(i)
        hd = [[i + 1 for i in atom] for atom in hd.values()]

        vd = defaultdict(list)
        for i, j in enumerate(self.vm):
            vd[j].append(i)
        vd = [[i + 1 for i in atom] for atom in vd.values()]

        hStab = libgap(hP).Stabilizer(hd, libgap.OnTuplesSets)
        vStab = libgap(vP).Stabilizer(vd, libgap.OnTuplesSets)
        hLiftedStab = libgap.PreImage(hH, hStab)
        vLiftedStab = libgap.PreImage(vH, vStab)
        return hLiftedStab.Intersection(hLiftedStab, vLiftedStab)

    def __hash__(self):
        return hash((tuple(self.hp), tuple(self.vp), tuple(self.hm), tuple(self.vm)))

    def __eq__(self, other):
        return (
            isinstance(other, ThurstonVeech)
            and self.hp == other.hp
            and self.vp == other.vp
            and self.hm == other.hm
            and self.vm == other.vm
        )

    def __ne__(self, other):
        return not (self == other)

    @classmethod
    @click.command(
        name="thurston-veech",
        cls=GroupedCommand,
        group="Surfaces",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option(
        "--horizontal-permutation", "-h", type=str, help="horizontal permutaiton"
    )
    @click.option("--vertical-permutation", "-v", type=str, help="vertical permutation")
    @click.option(
        "--horizontal-multiplicities", "-m", type=str, help="horizontal multiplicities"
    )
    @click.option(
        "--vertical-multiplicities", "-n", type=str, help="vertical multiplicities"
    )
    def click(
        horizontal_permutation,
        vertical_permutation,
        horizontal_multiplicities,
        vertical_multiplicities,
    ):
        pass


class ThurstonVeechs:
    r"""
    The translation surfaces obtained from Thurston-Veech construction.
    """

    @classmethod
    @click.command(
        name="thurston-veech",
        cls=GroupedCommand,
        group="Surfaces",
        help=__doc__.split("EXAMPLES")[0],
    )
    @click.option("--stratum", type=str, required=True)
    @click.option("--component", type=str, required=False)
    @click.option(
        "--nb-squares-limit",
        "-n",
        type=int,
        help="maximum number of squares",
        required=True,
    )
    @click.option(
        "--multiplicities-limit",
        "-m",
        type=int,
        required=True,
        help="maximum sum of twist multiplicities",
    )
    @click.option(
        "--literature",
        default="exclude",
        type=click.Choice(["exclude", "include", "only"]),
        help="also include ngons described in literature",
        show_default=True,
    )
    def click(stratum, component, nb_squares_limit, multiplicities_limit, literature):
        from surface_dynamics import AbelianStratum

        if not stratum.startswith("H(") or not stratum.endswith(")"):
            raise click.UsageError("invalid stratum argument")
        try:
            H = AbelianStratum(*[int(x.strip()) for x in stratum[2:-1].split(",")])
        except ValueError:
            raise click.UsageError("invalid stratum argument")

        if component == "hyp" or component == "hyperelliptic":
            H = H.hyperelliptic_component()
        elif component == "nonhyp" or component == "non-hyperelliptic":
            H = H.nonhyperelliptic_component()
        elif component == "even":
            H = H.even_component()
        elif component == "odd":
            H = H.odd_component()
        elif component is not None:
            raise click.UsageError("invalid component argument")

        seen = set()

        for c in H.cylinder_diagrams():
            for n in range(c.smallest_integer_lengths()[0], nb_squares_limit):
                for lh in c.widths_and_heights_iterator(n, height_one=True):
                    for o0 in c.cylcoord_to_origami_iterator(*lh):
                        o1 = o0.mirror()
                        o2 = o0.vertical_symmetry()
                        o3 = o0.horizontal_symmetry()

                        for o in [o0, o1, o2, o3]:
                            o.relabel(inplace=True)

                        if o0 > o1 or o0 > o2 and o0 > o3:
                            continue
                        # TODO: in case of equality above, we will generate the same
                        # origami twice.

                        cd1 = o1.cylinder_decomposition()
                        if any(h != 1 for _, _, _, h, _, _ in cd1):
                            continue

                        for mh in IntegerVectors(
                            multiplicities_limit, c.ncyls(), min_part=1
                        ):
                            for mv in IntegerVectors(
                                multiplicities_limit, len(cd1), min_part=1
                            ):
                                tv = ThurstonVeech(o.r_tuple(), o.u_tuple(), mh, mv)

                                if tv in seen:
                                    print("Skipping duplicate")
                                    continue

                                if literature == "include":
                                    pass
                                elif literature == "exclude":
                                    if tv.reference():
                                        continue
                                elif literature == "only":
                                    reference = tv.reference()
                                    if (
                                        reference is None
                                        or "Translation covering" in reference
                                    ):
                                        continue
                                else:
                                    raise NotImplementedError(
                                        "Unsupported literature value"
                                    )

                                seen.add(tv)
                                yield tv
