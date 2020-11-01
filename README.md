Automation scripts for the [flatsurf](https://github.com/flatsurf) stack to survey large sets of objects.

To perform a full survey, use [`python -m flatsurvey`](./flatsurvey/__main__.py). To investigate a single object, run [`python -m flatsurvey.worker`](./flatsurvey/worker/__main__.py).

For example, here is a typical survey that collects data about triangles, quadrilaterals, and pentagons:

```
nice python -m flatsurvey ngons --vertices 3 ngons --vertices 4 ngons --vertices 5 orbit-closure cylinder-periodic-direction log graphql
```

Dependencies:

- click Python module
- pinject Python module
- plumbum Python module
