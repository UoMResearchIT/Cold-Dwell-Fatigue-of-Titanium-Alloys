# Cold Dwell Fatigue of Titanium Alloys: History, Current State, and Aviation Industry Perspective [Supporting Software]

This is an unofficial "fork" of the package cited below, modified for headless execution on a Docker (Linux) environment.
See [Change Log](#change-log) for details about the current status and important modifications.

> [!CAUTION]
> This branch is a stripped-down version intended for command-line execution **only**. Use the `main` branch to access the original GUI-based implementation.


#### LICENSE: (?) Ask the original authors.

---

DOI : https://doi.org/10.21949/tzgj-rk36

Creator(s) : Pilchak, Adam;Fox, Kate;Payton, Eric;Wiedemann, Mirjam;Broderick, Tom;Delaleau, Pierre;Glavicic, Michael;Jenkins, Nigel;Ruppert, Jean-Manuel;Streich, Brian;Tsukada, Masayuki;Venkatesh, Vasisht;Woodfield, Andy;

Corporate Creator(s) : Pratt & Whitney;Materials Resources LLC;Rolls Royce Corp;University of Cincinnati;MTU Aero Engines;Air Force Research Laboratory (Wright-Patterson Air Force Base, Ohio);United States. Department of Transportation. Federal Aviation Administration;Safran Aircraft Engines;Safran Helicopter Engines;Honeywell Aerospace Engineering Advanced Technology;IHI Corp, Tokyo, Japan;GE Aerospace;

Corporate Contributor(s) : United States. Department of Transportation. Federal Aviation Administration. William J. Hughes Technical Center

Published Date : 2024-11-13

## Microtexture Quantification Workflow
> Automated routines were developed by a consortium of aerospace companies under Metals Affordability Initiative (MAI) programs to process and quantify microtexture in titanium. These routines were made available as part of the PW9 program for assessment and publicly released under PW24 program (2024). The tool is not intended to be perfect, but there is concensus among the industry that it appropriate for benchmark comparisons of materials and draw useful correlations for different processing routes, product forms, etc. The tool is provided “as is". Sse the software at your own risk. No warranties are provided as to performance, fitness for a particular purpose not outlined above, or any other warranties whether expressed or implied.

> The routines use open-source software Dream3D (version 6.5)[*] to perform EBSD file cleanup and feature quantification. Additional post-processing scripts were developed in Python to compute additional metrics and automate data post-processing.

[*] The original version uses Dream3D 6.5.49 (Windows), this fork has been tested with 6.5.171 (Linux).

> [Link to (Original) User Guide](/Documentation/Microtexture%20Analysis%20User%20Guide.pptx)

> This tool has been publicly released (AFRL-2024-4080)


## Usage

Clone this repository:
```sh
git clone https://github.com/UoMResearchIT/Cold-Dwell-Fatigue-of-Titanium-Alloys.git ./microtexture
cd ./microtexture
```

#### Using [Docker](https://docs.docker.com/engine/install/) (recommended)

```sh
docker buildx build . -t microtexture:latest
docker run --rm microtexture:latest --help
docker run --rm -v /path/to/my/data:/data microtexture:latest [OPTIONS] FILE
```

#### Local Installation

Requires Dream3D (version 6.5) and a python environment manager, e.g. [`uv`](https://uv.dev/):

```sh
export DREAM3D_PIPELINE_RUNNER=/path/to/Dream3D/PipelineRunner
uv sync
uv run python -m microtexture -h
```

## Change Log

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
