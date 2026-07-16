# PEOPLE-ECCO Solution / Algorithm base image

PEOPLE-ECCO solutions and algorithms are implemented as Python modules that plug into the shared execution contract defined by this repository. Each algorithm image supplies the domain-specific code and dependencies, while this base image supplies the common runtime behavior: openEO authentication, batch job tracking, CWL interface, Prefect integration, STAC result handling, and result persistence.

The algorithm itself is responsible for the scientific workflow: loading EO collections, building openEO process graphs, starting batch jobs, downloading or generating result assets, and adding those assets to the provided STAC catalog. The shared wrapper intercepts `conn.create_job(...)` so openEO batch jobs can be tracked, logged, and cost-tracked after execution.

## Algorithm image contract

An algorithm image is a Docker image `FROM` this base image that adds its own dependencies and source code. To work with either wrapper, it must fulfill the contract below.

### 1. Python interface

The image must expose an importable module with an `Algorithm` class implementing a static `run` method:

```python
from openeo.rest.connection import Connection
from pystac import Catalog

class Algorithm:
    @staticmethod
    def run(conn: Connection, catalog: Catalog, parameters: Dict) -> None:
        ...
```

The wrapper imports this module dynamically (via `importlib.import_module`), creates a pre-authenticated openEO connection, creates an empty PySTAC catalog for the run, and calls `Algorithm.run(conn, catalog, parameters)`, where:

- `conn`: an authenticated openEO connection to the Copernicus Data Space openEO federation.
- `catalog`: a PySTAC catalog that the algorithm must populate with result items and assets.
- `parameters`: the execution parameters submitted through the API, including the spatial extent derived from the selected timeseries.

### 2. Build-time image identity

The importable module path and the STAC solution identity are baked into the image at build time as Docker `ARG`s promoted to `ENV`, the same pattern already used for `ALGORITHM_BASE`. An algorithm Dockerfile must declare all three, e.g.:

```dockerfile
ARG ALGORITHM_BASE="bap.main"
ENV ALGORITHM_BASE=${ALGORITHM_BASE}

ARG SOLUTION="ECCO-SAV"
ENV SOLUTION=${SOLUTION}

ARG SOLUTION_VERSION="1.0.1"
ENV SOLUTION_VERSION=${SOLUTION_VERSION}
```

and the caller (Prefect deployment build, `docker build`, or the CWL `DockerRequirement`/`EnvVarRequirement`) must supply matching values.

| Variable | Required | Consumed by | Purpose |
|---|---|---|---|
| `ALGORITHM_BASE` | Yes | both wrappers | Dotted module path passed to `importlib.import_module(...)` to locate the `Algorithm` class. The Prefect wrapper does not validate this and will raise on import if unset/wrong; the CWL wrapper raises `ValueError` explicitly if unset. |
| `SOLUTION` | Recommended for provenance | `stac_metadata.build_stac_properties` | Human-readable solution identifier, e.g. `"ECCO-SAV"`. `null` in the STAC output if unset. |
| `SOLUTION_VERSION` | Recommended for provenance | `stac_metadata.build_stac_properties` | Version of the solution/algorithm, e.g. `"1.0.1"`. `null` in the STAC output if unset. |

### 3. Runtime environment variables

These are supplied when the container is run (as opposed to baked in at build time), and differ slightly between the two wrappers:

**`prefect_wrapper.py`** (openEO/S3 credentials come from Prefect `Secret` blocks — `ecco-openeo-client-id`, `ecco-openeo-client-secret`, `ecco-s3-url`, `ecco-s3-access-key`, `ecco-s3-secret-key` — not env vars):

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `OPENEO_BACKEND_URL` | No | `https://openeofed.dataspace.copernicus.eu/` | openEO federation URL to connect to. |
| `OPENEO_JOB_SCHEDULING_POLL_INTERVAL_SECONDS` | No | `15` | Poll interval while waiting for the active-job limit to clear (`openeo_util.py`). |
| `OPENEO_MAX_PARALLEL_ACTIVE_JOBS` | No | `5` | Max number of concurrent `queued`/`running` batch jobs for this openEO account before new job starts are throttled. |

**`cwl_wrapper.py`** (standalone execution, all inputs are plain env vars, typically populated via CWL's `EnvVarRequirement` from workflow inputs):

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `CDSE_CLIENT_ID` / `CDSE_CLIENT_SECRET` | Yes | — | openEO/CDSE OIDC client credentials. Raises `ValueError` if either is missing. |
| `PARAMETERS_FILE` | Yes | — | Path to a JSON file of algorithm parameters, loaded and passed to `Algorithm.run(...)`. |
| `OPENEO_BACKEND_URL` | No | `https://openeofed.dataspace.copernicus.eu/` | openEO federation URL to connect to. |
| `OPENEO_JOB_SCHEDULING_POLL_INTERVAL_SECONDS` | No | `15` | Poll interval while waiting for the active-job limit to clear (`openeo_util.py`). |
| `OPENEO_MAX_PARALLEL_ACTIVE_JOBS` | No | `5` | Max number of concurrent `queued`/`running` batch jobs for this openEO account before new job starts are throttled. |
| `RUN_NAME` | No | `ecco-cwl-run` | Identifier for the run; used as the STAC catalog id and as the sibling `run_name` field alongside `properties` in the persisted `ItemCollection`. |
| `OUTPUT_DIR` | No | `./output` | Local directory the STAC collection and result assets are written to. |

### 4. STAC result properties

After `Algorithm.run(...)` returns, both wrappers persist the populated catalog as a single STAC `ItemCollection`/`FeatureCollection`. Alongside `type` and `features`, they attach a top-level `properties` object built by `stac_metadata.build_stac_properties(...)`:

```json
{
    "type": "FeatureCollection",
    "properties": {
        "solution": "ECCO-SAV",
        "solutionVersion": "1.0.1",
        "cdseVersion": "1.2.0",
        "inputParameters": "{\"rangestart\": \"2021-06-01\", \"rangeend\": \"2021-06-30\"}",
        "executionDateTime": "2026-07-16T09:12:03+00:00"
    },
    "features": []
}
```

- `solution` / `solutionVersion`: from the build-time `SOLUTION` / `SOLUTION_VERSION` env vars described above.
- `cdseVersion`: fetched live from the openEO backend via `openeo_util.get_backend_version(conn)` (the backend's `capabilities().api_version()`), not baked into the image, since it reflects the backend's current state rather than the algorithm image's. `null` if the capabilities document couldn't be fetched.
- `inputParameters`: the `parameters` dict passed to `Algorithm.run(...)`, JSON-encoded as a string.
- `executionDateTime`: UTC timestamp (ISO 8601) taken at the moment the STAC result is persisted.

This contract is identical across both execution patterns, so downstream consumers of the STAC output can rely on the same `properties` shape regardless of how an algorithm was run.

# Build

The base image is build and published (via GitHub actions) on every new tag/release as `ghcr.io/people-ecco/ecco-algorithm-base:latest` and `ghcr.io/people-ecco/ecco-algorithm-base:<tag-version>`.

You can build it locally using:

```sh
docker build -t ghcr.io/people-ecco/ecco-algorithm-base:latest .
```