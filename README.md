[![tests](https://github.com/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys/actions/workflows/pytest.yml/badge.svg?branch=main)](https://github.com/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys/actions/workflows/pytest.yml)
[![codecov.io](https://codecov.io/github/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys/coverage.svg)](https://codecov.io/github/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys)

# Cold Dwell Fatigue of Titanium Alloys: History, Current State, and Aviation Industry Perspective [Supporting Software]

This is an unofficial "fork" of the package cited below, modified for headless execution on a Docker (Linux) environment.
See [Change Log](#change-log) for details about the current status and important modifications.

> [!IMPORTANT]
> This branch is an experimental rewrite of the original code, to go around the fact that 
> DREAM3D 6.5 is no longer maintained.
>
> The `nxrunner` pipeline templates are **AI translations** of the originals, and differ in some
> [particulars](#differences-between-dream3d-65-and-simplnx-pipelines).
> We have run a batch of [regression tests](#testing) that suggest the pipelines are equivalent
> within reasonable tolerances, but we strongly encourage you to do the same with your own data
> before using this version.

## TODOS

- Regression tests have not yet covered a case where "Pixel Fraction Altered By Cleanup" > 0. This might be a reporting artifact, a matter of adjusting the test `ARGS`, or we might just need sufficiently "dirty" data.

- If we're already moving to SIMPLNX, pipelines might be clearer and more maintainable if written as [python scripts](https://www.dream3d.io/python_docs/Tutorial_2.html) instead of `.d3dpipeline` Jinja templates. 


#### LICENSE: (?) Ask the original authors.

---

URL : https://rosap.ntl.bts.gov/view/dot/78565

Creator(s) : Pilchak, Adam;Fox, Kate;Payton, Eric;Wiedemann, Mirjam;Broderick, Tom;Delaleau, Pierre;Glavicic, Michael;Jenkins, Nigel;Ruppert, Jean-Manuel;Streich, Brian;Tsukada, Masayuki;Venkatesh, Vasisht;Woodfield, Andy;

Corporate Creator(s) : Pratt & Whitney;Materials Resources LLC;Rolls Royce Corp;University of Cincinnati;MTU Aero Engines;Air Force Research Laboratory (Wright-Patterson Air Force Base, Ohio);United States. Department of Transportation. Federal Aviation Administration;Safran Aircraft Engines;Safran Helicopter Engines;Honeywell Aerospace Engineering Advanced Technology;IHI Corp, Tokyo, Japan;GE Aerospace;

Corporate Contributor(s) : United States. Department of Transportation. Federal Aviation Administration. William J. Hughes Technical Center

Published Date : 2024-11-13

## Microtexture Quantification Workflow
> Automated routines were developed by a consortium of aerospace companies under Metals Affordability Initiative (MAI) programs to process and quantify microtexture in titanium. These routines were made available as part of the PW9 program for assessment and publicly released under PW24 program (2024). The tool is not intended to be perfect, but there is concensus among the industry that it appropriate for benchmark comparisons of materials and draw useful correlations for different processing routes, product forms, etc. The tool is provided “as is". Sse the software at your own risk. No warranties are provided as to performance, fitness for a particular purpose not outlined above, or any other warranties whether expressed or implied.

> The routines use open-source software Dream3D (version 6.5)[*] to perform EBSD file cleanup and feature quantification. Additional post-processing scripts were developed in Python to compute additional metrics and automate data post-processing.

[*] The original version uses Dream3D 6.5.49 (Windows), this fork has been tested with 6.5.171 (Linux). See [Change Log](#change-log) for details.

> [Link to (Original) User Guide](/Documentation/Microtexture%20Analysis%20User%20Guide.pptx)

> This tool has been publicly released (AFRL-2024-4080)


## Installation

Clone this repository:
```sh
git clone https://github.com/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys.git ./microtexture
cd ./microtexture
```

#### Using [pixi](https://pixi.prefix.dev/)

```sh
pixi install && pixi run setup-plugins
pixi shell
microtexture --help
```

> [!NOTE]
> `scripts/setup-plugins.sh` adds symlinks for `.simplnx` plugins, which `nxrunner` otherwise has problems finding.

#### Using conda / mamba

```sh
conda config --add channels conda-forge
conda config --set channel_priority strict
conda create -n nxpython python=3.12
conda activate nxpython
conda install -c bluequartzsoftware dream3dnx
pip install -e .
bash scripts/setup-plugins.sh
microtexture --help
```

#### Using [Docker](https://docs.docker.com/engine/install/)

The provided Dockerifile contains both the legacy DREAM3D 6.5.171 `PipelineRunner`, as well as the new `nxrunner`

```sh
docker buildx build . -t microtexture:simplnx
docker run --rm microtexture:simplnx --help
docker run --rm -v /path/to/my/data:/data microtexture:simplnx [OPTIONS] FILE
```

## Testing

> [!NOTE]
> Regression tests require `docker` to generate reference results using the "legacy" [v0.3.0-cli](https://github.com/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys/tree/v0.3.0-cli) version. They will be skipped if Docker is not available.

The tests are parametrized, and will pick up any `*.ang` and/or `*.ctf` files you drop on the `sample_data` directory. 
Results will become available for inspection on `src/microtexture/tests/.cache`.
You might have to tweak the default test `ARGS` to match your data -- `min_mtr_size` in particular seems to have a very strong effect on  metrics
(if not enough MTRs are found, statistics become unstable).

Install additional `dev` dependencies, and run tests using `pytest`, e.g.:

```sh
pixi install -e dev && pixi run -e dev setup-plugins
pixi run -e dev pytest -q
```

Or using Docker:
```sh
docker compose -f docker-compose-test.yaml up
```

## Differences Between DREAM3D 6.5 and SIMPLNX Pipelines

The original workflow (publication reference above) used DREAM3D 6.5.49. Already with v0.3 we had to make minor tweaks to use the available Linux binary 6.5.171 (see [change log](#change-log)).

The transition to `nxrunner` with v0.5 requried a complete rewrite of the 
The reference pipeline uses DREAM3D 6.5.171 and its `PipelineRunner`. The SIMPLNX (`nxrunner`) port introduces differences that require workarounds:

The backend (DREAM3D-6.5 `PipelineRunner` vs SIMPLNX `nxrunner`) is auto-detected from the executable name passed to `--pipeline-runner`. 
If you still need DREAM3D 6.5 `PipelineRunner`, use `--pipeline-runner /path/to/PipelineRunner`.

> [!IMPORTANT]
> Subsections below are a curated summary of [Big Pickle](https://opencode.ai/docs/zen/)'s excuses to why the NX pipelines don't produce exactly the same results
> as the reference version. You might want to take them with a pinch of salt.


#### CrystalStructures conversion to Hexagonal

The original DREAM3D 6.5 `CAxisSegmentFeatures` filter accepts any crystal structure. Its SIMPLNX replacement (`nx::core::CAxisSegmentFeaturesFilter`) was consolidated to only allow Hexagonal (HCP) phases — if any phase in the data is not Hexagonal, the filter fails with error -8363.

The workaround (applied in both CTF and ANG pipeline templates):
1. **Backup** the original `CrystalStructures` array
2. **Replace** it with a new all-zeros array (all Hexagonal)
3. **Run** C-Axis segmentation (now succeeds)
4. **Restore** the original crystal structures

Without this step, multi-phase EBSD files (e.g. Ti64 with both HCP-α and BCC-β phases) crash the pipeline.

#### Parameter compatibility

Some filter parameters changed between DREAM3D-6.5 and SIMPLNX:
- `ReadCtfData`: requires `"DegreesToRadians": 0` to match the DREAM3D 6.5 behavior (angles were already in radians in CTF files)
- `ReadAngData`: the NX port introduces a `ConvertToRadians` flag (default `true`) that must be explicitly set to match expectations
- Array creation filters use `create_attribute_array_path` / `output_array_path` keys instead of the older naming conventions
- Tuple dimension flags (`set_tuple_dimensions`) must be set correctly to inherit dimensions from the parent attribute matrix

#### Numerical differences

Despite the workarounds, SIMPLNX does not produce bit-identical results to the reference DREAM3D-6.5 pipeline. Two sources of differences have been identified:

1. **RotateSampleRefFrameFilter interpolation** — An identity rotation (present in both pipelines) produces boundary pixels with interpolated values differing between backends.
2. **Cleanup filter neighbor selection** — `ReplaceElementAttributesWithNeighborValues` selects different neighbor orientations for cells adjacent to high-confidence (BC ≥ threshold) pixels.

The perturbed cells (typically < 0.1% of the scan) cascade through segmentation, causing a small number of features to merge or split differently. The downstream effect on per-class statistics is usually within 1.5%, but can blow up to ~20% if the clean-up thresholds are not well suited to the test data (summery metrics become
unstable for a small number of MTRs).

Matching and comparing individual MTRs seems to be more robust (differences of 0.1%–2.5% depending on the metric), given the right data, they might suffer from the same issues as the summary tests.


## Change Log

### v0.5.0 (2026-06) -- WIP

- Support for `nxrunner` as an alternative DREAM3D backend:
    - `*_nx.j2` template translations
    - _pixi/conda_ environment instead of _docker + uv_
    - changes to `postprocess.py` to support modified `*.dream3d` structure.
- Centroids added to `Raw_Data.csv` (to help in tracking individual features through backends)
- Regression tests include per-feature matching via 3D centroid+area nearest-neighbor, with P99-based column tolerances

### v0.4.0 (2026-06)

- JSON summary output
- Basic regression/postprocessing tests
- Docker image builds on ghcr.io/uomresearchit/dream3d:6.5.171 (DREAM3D 6.5.x no longer available for download)

### v0.3.0 (2026-01)

- Update pipelines to Dream3D 6.5.171

    The packaged DREAM3D 6.5.171 did not complain when loading the original pipeline (developed for 6.5.49),
    but it would actually execute updated versions of all filters. The pipeline templates have been updated to
    reflect this. The only relevant changes seem to be:

    - The new `ReadCtfData` filter on the CTF pipeline has a `DegreesToRadians` parameter, set to 0 to restore the original behavior.
    - The new `CAxisSegmentFeatures` filter contains a [bug fix](https://github.com/BlueQuartzSoftware/DREAM3D/commit/499e8bcb3dcf41e86f2c611f3cef6c5919432772) related to grouping voxels with identical orientation values. The updated pipeline tends to detect slightly more MTRs across all classes. Differences for most summary metrics are in the order of 1%-2%.

- Unit test, and bug fixes for CLI wrapper
- Write markdown version of summary report


### v0.2.1 (2025-12)
- Porting to a Linux environment, minor bug fixes, linting & cleanup.
- Configuration through `.env` / `yaml` (see below)
- Restructuring to fit canonical Python package layout
- Command line interface (independent from GUI)
    - Simplified templating using Jinja2
    - (Missing!) support for multiple files
    - Post-processing (analysis) logic separated from GUI

### v0.2.1-cli
- Command line interface only (no GUI)

### TODO

- Support for multiple files in command line interface
- Unit tests

