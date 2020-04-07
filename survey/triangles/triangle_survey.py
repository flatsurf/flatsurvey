#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Typical usage
#
#    $ sage -python triangle_survey.py 2 4 7 --bound 3 --test-complete-periodicity True
#    $ sage -python triangle_survey.py 2 4 11 --bound 4 --test-complete-periodicity False
#
######################################################################
#  This file is part of flatsurf.
#
#        Copyright (C) 2019-2020 Julian Rüth
#                      2020 Vincent Delecroix
#
#  flatsurf is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  flatsurf is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with flatsurf. If not, see <https://www.gnu.org/licenses/>.
######################################################################

import argparse
import sys

from sage.all import gcd, QQ
from sage.arith.all import gcd
import flatsurf

def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

parser = argparse.ArgumentParser(description='Survey a Triangle')
parser.add_argument('angles', metavar='N', type=int, nargs='+')
parser.add_argument('--bound', type=int, default=10, help="bound for the length of saddle connections")
parser.add_argument('--depth', type=int, default=512, help="depth for the flow decomposition")
parser.add_argument('--test-complete-periodicity', type=str2bool, default=True, help="whether to look for complete periodicity")

args = parser.parse_args()

assert len(args.angles) == 3
a,b,c = args.angles
if gcd([a, b, c]) != 1:
    raise ValueError

print("Unfolding %s"%(args.angles))

# Unfold the (a, b, c) triangle with sage-flatsurf
E = flatsurf.EquiangularPolygons(*args.angles)
T = E([1])
S = flatsurf.similarity_surfaces.billiard(T, rational=True)
S = S.minimal_cover(cover_type="translation")

# Dynamical orbit closure computation
O = flatsurf.GL2ROrbitClosure(S)
print("ambient vector space dimension: %d"%O._U.nrows())
print("number field degree: %d"%O.base_ring().degree())
print(O._surface) # underlying pyflatsurf surface

# Prediction for orbit closure
ambient_locus = E.billiard_unfolding_stratum("half-translation")
ambient_dim = ambient_locus.dimension()
quad = (ambient_locus != E.billiard_unfolding_stratum("translation"))

sc_completely_periodic = True
cyl_completely_periodic = True
parabolic = True
undetermined = 0
explored = 0

# TODO: we might want to move that in GL2ROrbitClosure
# TODO: there is a lot of redundancy here since we have some rotation invariance
# (see https://github.com/flatsurf/sage-flatsurf/issues/35)
def decomposition_sample(O):
    max_norm2 = None
    explored = set()
    for e in O._surface.edges():
        v = O._surface.fromEdge(e.positive())
        v = O.V2sage(O.V2(v))
        if max_norm2 is None:
            max_norm2 = v[0]**2 + v[1]**2
        else:
            max_norm2 = max(max_norm2, v[0]**2 + v[1]**2)
        if v[1]:
            v /= v[1]
        else:
            v /= v[0]
        v.set_immutable()
        if v not in explored:
            yield O.decomposition(v, limit=args.depth)
            explored.add(v)

    # consider unvisited directions twice as long as the edges
    for d in O.decompositions_depth_first(2*max_norm2, args.depth, visited=explored):
        yield d

    # pick edges of size what was asked in the script
    for d in O.decompositions_depth_first(args.bound, args.depth, visited=explored):
        yield d

# computation
dim = O.dimension()
for d in decomposition_sample(O):
    print("Investigating in direction %s "%d.u, end='')
    sys.stdout.flush()
    explored += 1
    
    ncyl, nmin, nund = d.num_cylinders_minimals_undetermined()
    print("decomposes into %d cylinders and %d minimal components and %d undetermined" % (ncyl, nmin, nund))
    if nund:
        undetermined += 1
        continue

    if args.test_complete_periodicity:
        if sc_completely_periodic or cyl_completely_periodic or parabolic:
            cyl_completely_periodic = cyl_completely_periodic and (ncyl == 0 or nmin == 0)
            sc_completely_periodic = sc_completely_periodic and (nmin == 0)

            if ncyl and parabolic:
                parabolic = parabolic and d.parabolic()

    O.update_tangent_space_from_flow_decomposition(d)
    new_dim = O.dimension()
    if new_dim != dim:
        print("new tangent vector(s): dimension increase from %d/%d to %d/%d" % (dim, ambient_dim, new_dim, ambient_dim))
        dim = new_dim
    if dim == ambient_locus.dimension() and (not args.test_complete_periodicity or not cyl_completely_periodic):
        print("nothing more to be investigated")
        break
else:
    print("up to bound %s on the length of saddle connection"%args.bound)

closure_dim = O.dimension()
absolute_dim = O.absolute_dimension()
print("Unfolding %s"%(args.angles))
print("%d directions explored (%d undetermined)"%(explored, undetermined))
if quad:
    print("ambient locus: %s inside %s (of dimension %s)"%(ambient_locus, ambient_locus.orientation_cover(), ambient_locus.dimension()))
else:
    print("ambient locus: %s (of dimension %s)"%(ambient_locus, ambient_locus.dimension()))
print("orbit closure dimension: %d"%closure_dim)
print("rank: %s"%QQ((absolute_dim,2)))

if args.test_complete_periodicity:
    if sc_completely_periodic and undetermined:
        print("saddle connection completely periodic: ? (probably false)")
    else:
        print("saddle connection completely periodic: %s"%sc_completely_periodic)
    if cyl_completely_periodic and undetermined:
        print("cylinder completely periodic: ? (probably true)")
    else:
        print("cylinder completely periodic: %s"%cyl_completely_periodic)
    if parabolic and undetermined:
        print("parabolic: ? (probably true)")
    else:
        print("parabolic: %s"%parabolic)
else:
    print("saddle connection completely periodic: untested")
    print("cylinder completely periodic: untested")
    print("parabolic: untested")
