Automation scripts for the [flatsurf](https://github.com/flatsurf) stack to
survey large sets of objects.

To perform a full survey, use [`flatsurvey`](./flatsurvey/survey.py). To
investigate a single object, run
[`flatsurvey-worker`](./flatsurvey/worker.py).

# Local Usage

To play with this tool locally, you can run `pixi shell` to make sure that you
have all the required dependencies installed in the correct versions.

Here, we check that the (1, 1, 1, 6) quadrilateral has dense orbit closure::

```sh
flatsurvey-worker ngon -a 1 -a 1 -a 1 -a 6 orbit-closure --deform
```

Here is a typical survey that collects data about triangles, quadrilaterals, and pentagons:

```sh
mkdir -p surveyname
nice flatsurvey ngons --vertices 3 ngons --vertices 4 ngons --vertices 5 orbit-closure --deform json --prefix=./surveyname
```

This will run indefinitely, so you want to stop this at some point with C-c.

To use the results of this survey to speed up a future survey, we collect the results in one `survey-results/orbit_closure.json`:

```sh
flatsurvey-maintenance join --outdir survey-results surveyname/*.json
```

And then use that JSON file as a database for the next run:

```sh
nice flatsurvey ngons --vertices 3 ngons --vertices 4 ngons --vertices 5 orbit-closure --deform local-cache --json orbit-closure.json json --prefix=./surveyname
```

# Cluster Surveys

We provide example scripts that run surveys on the PlaFRIM cluster. It should
be easy to adapt these to work on any cluster that can run a dask workload.

Setup this pixi repository for the scheduler and the workers:

```sh
sh plafrim/create-env.sh
```

Spawn a dask scheduler (here we call our survey `flatsurvey-3`):

```
sh plafrim/spawn-scheduler.sh flatsurvey-3
```

Reserve resources in your cluster:

```
salloc --ntasks=768 --time=13:30:00 --constraint="diablo|bora|brise|sirocco|zonda|miriel|souris|kona"
```

Spawn the workers:

```
for host in $(scontrol show hostnames); do sleep 1; srun --nodes=1 --ntasks=1 --exclusive -w $host sh plafrim/provision-env.sh flatsurvey-3 & done
wait
srun sh plafrim/spawn-worker.sh flatsurvey-3
```

Start the survey:

```
sh plafrim/survey.sh flatsurvey-3 "ngons --vertices 3"
```

Post-process the survey:

```
sh plafrim/postprocess.sh flatsurvey-3
```

...

# Troubleshooting

* For large surveys, RAM might become the limiting factor. It appears that we
  are not actually leaking memory but are hit by memory fragmentation during
  the Boshernitzan criterion. The issue can be fully mitigated by replacing
  malloc with [Mesh](https://github.com/plasma-umass/Mesh), i.e., setting
  `LD_PRELOAD=/path/to/libmesh.so`.
* SageMath (or one of its dependencies) might decide that it's beneficial to
  parallelize things further. However, this can easily overload a system.
  Typically, some linear algebra might spawn a process for each CPU on the
  system which could then easily lead to CPU² many processes if you run a
  lengthy survey. To disable this behaviour, set `MKL_NUM_THREADS=1
  OMP_NUM_THREADS=1 SAGE_NUM_THREADS=1`.
