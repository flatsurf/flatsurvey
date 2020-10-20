r"""
Translation surfaces coming from Thurston-Veech constructions

EXAMPLES::

    >>> from survey.sources.thurston_veech import ThurstonVeech
    >>> ThurstonVeech('(1,2)', '(1,3)', [1,1], [1,1]).surface()
    TranslationSurface built from 3 polygons
"""
#*********************************************************************
#  This file is part of flatsurf.
#
#        Copyright (C) 2020 Vincent Delecroix
#
#  Flatsurf is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Flatsurf is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurf. If not, see <https://www.gnu.org/licenses/>.
#*********************************************************************

import click

from sage.all import cached_method, IntegerVectors

from .surface import Surface
from flatsurvey.ui.group import GroupedCommand

from flatsurvey.pipeline.util import PartialBindingSpec

class ThurstonVeech(Surface):
    r"""
    Thurston-Veech construction
    """
    def __init__(self, hp, vp, hm, vm):
        self.hp = hp
        self.vp = vp
        self.hm = hm
        self.vm = vm

    @property
    def orbit_closure_dimension_upper_bound(self):
        # TODO: this does not detect quadratic differential coverings!
        return self.ambient_stratum().dimension()

    def __repr__(self):
        return "ThurstonVeech({}, {}, {}, {})" % (self.hp, self.vp, self.hm. self.vm)

    def reference(self):
        # TODO: square-tiled
        # TODO: translation coverings (via the symmetry of the coordinates)
        # TODO: known exotic loci
        return

    @cached_method
    def origami(self):
        return self._thurston_veech()

    @cached_method
    def _thurston_veech(self):
        from flatsurf.geometry.thurston_veech import ThurstonVeech
        return ThurstonVeech(self.hp, self.vp, as_tuple=True)

    @cached_method
    def _surface(self):
        return self._thurston_veech()(self.hm, self.vm)

    @classmethod
    @click.command(name="thurston-veech", cls=GroupedCommand, group="Surfaces", help=__doc__.split('EXAMPLES')[0])
    @click.option("--horizontal-permutation", "-h", type=str, help="horizontal permutaiton")
    @click.option("--vertical-permutation", "-v", type=str, help="vertical permutation")
    @click.option("--horizontal-multiplicities", "-m", type=str, help="horizontal multiplicities")
    @click.option("--vertical-multiplicities", "-n", type=str, help="vertical multiplicities")
    def click(horizontal_permutation, vertical_permutation, horizontal_multiplicities, vertical_multiplicities):
        pass

class ThurstonVeechs:
    r"""
    The translation surfaces obtained from Thurston-Veech construction.
    """
    @classmethod
    @click.command(name="thurston-veech", cls=GroupedCommand, group="Surfaces", help=__doc__.split('EXAMPLES')[0])
    @click.option("--stratum", type=str, required=True)
    @click.option("--component", type=str, required=False)
    @click.option("--nb-squares-limit", "-n", type=int, help="maximum number of squares")
    @click.option("--multiplicities-limit", "-m", type=int, help="maximum sum of twist multiplicities")
    def click(stratum, component, nb_squares_limit, multiplicities_limit):
        print(stratum)
        print(component)
        print(nb_squares_limit)
        print(multiplicities_limit)
        from surface_dynamics import AbelianStratum
        if not stratum.startswith('H(') or not stratum.endswith(')'):
            raise click.UsageError("invalid stratum argument")
        try:
            H = AbelianStratum(*[int(x.strip()) for x in stratum[2:-1].split(',')])
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
                        if any(h != 1 for _,_,_,h,_,_ in cd1):
                            continue

                        for mh in IntegerVectors(multiplicities_limit, c.ncyls()):
                            for mv in IntegerVectors(multiplicities_limit, len(cd1)):
                                yield ThurstonVeech(o.r_tuple(), o.u_tuple(), mh, mv)
