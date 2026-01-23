[![tests](https://github.com/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys/actions/workflows/pytest.yml/badge.svg?branch=main)](https://github.com/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys/actions/workflows/pytest.yml)
[![codecov.io](https://codecov.io/github/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys/coverage.svg)](https://codecov.io/github/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys)

# Cold Dwell Fatigue of Titanium Alloys: History, Current State, and Aviation Industry Perspective [Supporting Software]

This is an unofficial "fork" of the package cited below, modified for headless execution on a Docker (Linux) environment.
See [Change Log](#change-log) for details about the current status and important modifications.


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


## Usage

Clone this repository:
```sh
git clone https://github.com/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys.git ./microtexture
cd ./microtexture
```

#### Using [Docker](https://docs.docker.com/engine/install/) (recommended)

To run the `microtexture` GUI:
```sh
# TEST_DATA will be mounted to /data in the container
export TEST_DATA=/path/to/my/data
docker compose up --build
```

To run headless (command line):
```sh
docker buildx build . -t microtexture:latest
docker run --rm microtexture:latest --help
docker run --rm -v /path/to/my/data:/data microtexture:latest [OPTIONS] FILE
```

> [!TIP]
> If you only need the command line interface, consider using the `cli` branch of this repository, which has been streamlined for this purpose.

To run the DREAM3D GUI (e.g. for development of new pipelines):
```sh
docker compose -f docker-compose-dream3d-gui.yaml up --build
```

#### Local Installation

Requires Dream3D (version 6.5) and a python environment manager, e.g. [`uv`](https://uv.dev/):

```sh
export DREAM3D_PIPELINE_RUNNER=/path/to/Dream3D/PipelineRunner
uv sync
uv run python -m microtexture -h
```

To run the GUI:
```sh
uv run python -m microtexture gui
```


## Change Log

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

### TODO

- Support for multiple files in command line interface
- Single configuration file for both GUI and CLI
- Rewrite GUI as an interface to the command line tool
    - Use Jinja2 templates for GUI as well
    - Use the `postprocess` module
- The GUI could do with some linting and refactoring for readability
- Unit tests
