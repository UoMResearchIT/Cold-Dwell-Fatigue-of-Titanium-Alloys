"""
For every *.ang and *.ctf file in sample_data, compares results produced with
the dockerized v0.3.0-cli and the current code version.

Results are saved to tests/.cache/<file-stem> for inspection (cleared before test re-runs).
"""

import os
import shutil
import subprocess
from importlib.resources import files

import pandas as pd
import pytest

if not shutil.which("docker"):
    pytest.skip("Regression tests require docker!", allow_module_level=True)

CACHE_DIR = files("microtexture") / "tests/.cache"
REUSE_REF = True
TOLERANCE = {"relative": 1e-4, "absolute": 1e-6}

_SAMPLE_DATA = files("microtexture") / "sample_data"
_TEST_FILES = sorted(_SAMPLE_DATA.glob("*.ctf")) + sorted(_SAMPLE_DATA.glob("*.ang"))

ARGS = {
    "ci_mask_threshold": 0.05,
    "iq_mask_threshold": 20000.0,
    "ci_primary_threshold": 0.05,
    "ci_secondary_threshold": 0.1,
    "error_mask_threshold": 1,
    "bc_primary_threshold": 30,
    "bc_secondary_threshold": 50,
    "caxis_misalignment": 20.0,
    "min_mtr_size": 5000,
    "stress_axis": "001",
}

_EXPECTED_FILES = [
    "{stem}.dream3d",
    "{stem}.json",
    "{stem}.xdmf",
    "{stem}_IPF_Average_Z.tif",
    "{stem}_IPF_Cleaned_Z.tif",
    "{stem}_IPF_MTR_Z.tif",
    "{stem}_IPF_Raw_Z.tif",
    "PoleFigures/Cleaned_Pole_Figure_Phase_1.pdf",
    "PoleFigures/MTR_Pole_Figure_Phase_1.pdf",
    "PoleFigures/Thresholded_Pole_Figure_Phase_1.pdf",
]

_OPTIONAL_FILES = [
    "PoleFigures/Cleaned_Pole_Figure_Phase_2.pdf",
    "PoleFigures/Thresholded_Pole_Figure_Phase_2.pdf",
]

_ANALYSIS_FILES = [
    "Raw_Data.csv",
    "Individual_MTRs.png",
    "Microtexture_Statistics_Summary.xlsx",
    "Microtexture_Statistics_Summary.md",
    "Microtexture_Statistics_Summary.json",
]
for axis in ["X", "Y", "Z"]:
    _ANALYSIS_FILES.extend(
        [
            f"IPF_Images/{axis}/IPF_Cleaned_{axis}_Image_w_Scalebar.png",
            f"IPF_Images/{axis}/IPF_MTR_{axis}_Image_w_Scalebar.png",
        ]
    )


def expected_files(stem, ref_dir=None):
    """
    Return rendered templates for _EXPECTED_FILES,
    plus any _OPTIONAL_FILES that exist in ref_dir
    """

    files = [f.format(stem=stem) for f in _EXPECTED_FILES]
    if not ref_dir:
        return files

    opt = [f.format(stem=stem) for f in _OPTIONAL_FILES]
    for f in opt:
        if (ref_dir / f).is_file():
            files.append(f)

    return files


def cli_args(args):
    d = {"--" + k.replace("_", "-"): str(v) for k, v in args.items()}
    return [x for i in d.items() for x in i]


@pytest.fixture(params=_TEST_FILES, ids=lambda p: p.stem, scope="session")
def test_file(request):
    yield request.param


@pytest.fixture(scope="session")
def reference_results(test_file):

    key = test_file.stem
    results_dir = CACHE_DIR / "reference" / key
    if results_dir.is_dir() and not REUSE_REF:
        shutil.rmtree(results_dir)
    os.makedirs(results_dir, exist_ok=True)

    if not os.path.isfile(results_dir / f"{key}.dream3d"):
        # fmt: off
        subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{test_file.parent}:/data",
                "-v", f"{results_dir }:/results",
                "--user", f"{os.getuid()}:{os.getgid()}",
                "ghcr.io/uomresearchit/cold-dwell-fatigue-of-titanium-alloys:v0.3.0-cli",
            ] +
            cli_args(ARGS) +
            [
                "-o", "/results",
                "-v",
                f"/data/{test_file.name}",
            ],
            check=True,
        )
        # fmt: on

    yield results_dir


def test_reference_available(reference_results):
    """Check that the expected results files have been generated"""

    for relpath in expected_files(reference_results.name):
        path = reference_results / relpath
        assert path.is_file(), f"Expected file not found: {path}"
        assert os.path.getsize(path) > 0, f"File is empty: {path}"


@pytest.fixture(scope="session")
def current_results(test_file):

    from microtexture.cli import parse_args, main

    results_dir = CACHE_DIR / "results" / test_file.stem
    if results_dir.is_dir():
        shutil.rmtree(results_dir)
    os.makedirs(results_dir, exist_ok=True)

    # fmt: off
    args = parse_args(
        cli_args(ARGS) +
        [
            "-o", str(results_dir),
            "--no-analysis",
            "-v",
            str(test_file),
        ]
    )
    # fmt: on

    main(args)

    yield results_dir


def test_current(reference_results, current_results):
    """Check that the expected results files have been generated"""

    for filename in expected_files(current_results.name, reference_results):
        path = current_results / filename
        assert path.is_file(), f"Expected file not found: {path}"
        assert os.path.getsize(path) > 0, f"File is empty: {path}"


def run_analysis(results, analysis_dir):

    from microtexture.postprocess import analyzeData

    stem = results.name
    if analysis_dir.is_dir():
        shutil.rmtree(analysis_dir)
    os.makedirs(analysis_dir, exist_ok=True)

    dream3d_file = results / f"{stem}.dream3d"
    analyzeData(
        dream3d_file=dream3d_file,
        output_dir=analysis_dir,
        stress_axis=ARGS["stress_axis"],
        min_mtr_size=ARGS["min_mtr_size"],
        summary_format=["excel", "markdown", "json"],
    )

    for filename in _ANALYSIS_FILES:
        path = analysis_dir / filename
        assert path.is_file(), f"Expected file not found: {path}"
        assert os.path.getsize(path) > 0, f"File is empty: {path}"


@pytest.fixture(scope="module")
def redone_analysis(reference_results):
    """Current post-processing code run on reference results"""

    analysis_dir = reference_results / "analysis"
    run_analysis(reference_results, analysis_dir)
    yield analysis_dir


@pytest.fixture(scope="module")
def new_analysis(current_results):
    """Current post-processing code run on current results"""

    analysis_dir = current_results / "analysis"
    run_analysis(current_results, analysis_dir)
    yield analysis_dir


def test_redo_reference_analysis(reference_results, redone_analysis):
    compare_summaries(reference_results, redone_analysis)


def test_current_summaries(reference_results, new_analysis):
    compare_summaries(reference_results, new_analysis)


def read_summary(summary_file):

    tables = {}
    with open(summary_file, "r") as f:
        lines = f.readlines()

    current_table = None
    for line in lines:
        line = line.strip()
        if line.startswith("###"):
            current_table = line[3:].strip()
            tables[current_table] = []
        elif (
            current_table
            and line.startswith("|")
            and not set(line) <= {"|", "-", ":", " "}
        ):
            row = [cell.strip() for cell in line.split("|")[1:-1]]
            tables[current_table].append(row)

    for key, rows in tables.items():
        if len(rows) < 2:
            continue
        header = rows[0]
        data = rows[1:]
        df = pd.DataFrame(data, columns=header)
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except ValueError:
                pass
        tables[key] = df

    return tables


def compare_summaries(reference_analysis, new_analysis):

    ref_tables = read_summary(reference_analysis / "Microtexture_Statistics_Summary.md")
    gen_tables = read_summary(new_analysis / "Microtexture_Statistics_Summary.md")

    for key in ref_tables.keys():
        assert key in gen_tables, f"Missing table: {key}"
        ref_df = ref_tables[key]
        gen_df = gen_tables[key]

        for col in ref_df.columns:
            pd.testing.assert_series_equal(
                ref_df[col],
                gen_df[col],
                check_names=False,
                check_dtype=False,
                rtol=TOLERANCE["relative"],
                atol=TOLERANCE["absolute"],
            )
