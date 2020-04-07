Rank one
---------

The following should exhaust the list of known case of dimension 2 orbit closures
```
        if ((a == b == 1) or            # Veech 1989
            (a == 1 and b == c) or      # = (2,b,b) of Veech for b even
            (a == 1 and c == b + 1) or  # ~ (2,b,b) of Veech
            (a == 2 and c == b + 2) or  # Veech 1989
            (a == 2 and b == c) or      # Veech 1989
            (a == 1 and b == 2 and c%2 == 1) or  # Ward 1998
            (a == 4 and b == c) or      # ~ (2,b,b+2) of Veech
            (a,b,c) in [(3,3,4),
                        (2,3,4),  # Kenyon-Smillie 2000 acute triangle
                        (3,4,5),  # idem (first appeared in Veech 1989)
                        (3,5,7),  # idem (first appeared in Vorobets 1996)
                        (1,4,7),  # Hooper "Another Veech triangle"
                        ]
            ):
```

Two rank one examples do not belong to there

```
[1, 3, 6]
1260 directions explored (0 undetermined)
ambient locus: Q_2(4, 1, -1) inside H_4(2^3) (of dimension 5)
orbit closure dimension: 3
rank: 1
saddle connection completely periodic: False
cylinder completely periodic: True
parabolic: False
```
and
```
Unfolding [1, 3, 8]
2676 directions explored (0 undetermined)
ambient locus: Q_1(2^2, -1^4) inside H_3(1^4) (of dimension 6)
orbit closure dimension: 4
rank: 1
saddle connection completely periodic: False
cylinder completely periodic: True
parabolic: False
```

Rank two
--------

```
Unfolding [1, 4, 11]
3712 directions explored (0 undetermined)
ambient locus: Q_2(9, -1^5) inside H_6(10) (of dimension 8)
orbit closure dimension: 4
rank: 2
```
This is also the Eskin-McMullen-Mukamel-Wright quadrilateral (?, ?, ?, ?)

```
Unfolding [1, 4, 15]
7120 directions explored (20 undetermined)
ambient locus: Q_2(1^5, 0^2, -1) inside H_6(2^5, 0^4) (of dimension 10)
orbit closure dimension: 6
rank: 2
```
This is also the Eskin-McMullen-Mukamel-Wright quadrilateral (?, ?, ?, ?)

```
Unfolding [3, 4, 13]
2700 directions explored (0 undetermined)
ambient locus: Q_4(11, 1, 0^2) inside H_8(12, 2, 0^4) (of dimension 10)
orbit closure dimension: 6
rank: 2
```
This one is new, expected to be the same orbit closure as the quadrilateral (2, 2, 3, 13)

Full rank codimension one
-------------------------

There is a whole bunch of full rank codimension one that seems to come from covering
of quadratic differentials on the sphere. They all have the pattern (a, a, 2b+1).
