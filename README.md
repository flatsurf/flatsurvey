Automation scripts for the [flatsurf](https://github.com/flatsurf) stack to survey large sets of objects.

To perform a full survey, use [`flatsurvey`](./flatsurvey/__main__.py). To investigate a single object, run [`flatsurvey-worker`](./flatsurvey/worker/__main__.py).

For example, here is a typical survey that collects data about triangles, quadrilaterals, and pentagons:

```
nice flatsurvey ngons --vertices 3 ngons --vertices 4 ngons --vertices 5 orbit-closure log graphql
```

# Troubleshooting

* For large surveys, RAM might become the limiting factor. It appears that we are not actually leaking memory but are hit by memory fragmentation during the Boshernitzan criterion. The issue can be fully mitigated by replacing malloc with [Mesh](https://github.com/plasma-umass/Mesh), i.e., setting `LD_PRELOAD=/path/to/libmesh.so`.
