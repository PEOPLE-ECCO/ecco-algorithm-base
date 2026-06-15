# PEOPLE-ECCO Solution / Algorithm base image

PEOPLE-ECCO solutions and algorithms are implemented as Python modules that plug into the shared execution contract defined by this repository. Each algorithm image supplies the domain-specific code and dependencies, while this base image supplies the common runtime behavior: openEO authentication, batch job tracking, CWL interface, Prefect integration, STAC result handling, and result persistence.

An algorithm module exposes an `Algorithm` class with a static `run` method:

```python
from openeo.rest.connection import Connection
from pystac import Catalog

class Algorithm:
    @staticmethod
    def run(conn: Connection, catalog: Catalog, parameters: Dict) -> None:
        ...
```

The module is selected at runtime through the `ALGORITHM_BASE` environment variable. The wrapper imports this module dynamically, creates a pre-authenticated openEO connection, creates an empty PySTAC catalog for the run, and calls `Algorithm.run(...)` with:

- `conn`: an authenticated openEO connection to the Copernicus Data Space openEO federation.
- `catalog`: a PySTAC catalog that the algorithm populates with result items and assets.
- `parameters`: the execution parameters submitted through the API, including the spatial extent derived from the selected timeseries.

The algorithm itself is responsible for the scientific workflow: loading EO collections, building openEO process graphs, starting batch jobs, downloading or generating result assets, and adding those assets to the provided STAC catalog. The shared wrapper intercepts `conn.create_job(...)` so openEO batch jobs can be tracked, logged, and cost-tracked after execution.

# Build

The base image is build and published (via GitHub actions) on every new tag/release as `ghcr.io/people-ecco/ecco-algorithm-base:latest` and `ghcr.io/people-ecco/ecco-algorithm-base:<tag-version>`.

You can build it locally using:

```sh
docker build -t ghcr.io/people-ecco/ecco-algorithm-base:latest .
```