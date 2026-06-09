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


CACHE_DIR = files("microtexture") / "tests/.cache"

ARGS = {"stress_axis": "100", "min_mtr_size": 10001}
TOLERANCE = {"relative": 1e-4, "absolute": 1e-6}

_SAMPLE_DATA = files("microtexture") / "sample_data"
_TEST_FILES = sorted(_SAMPLE_DATA.glob("*.ctf")) + sorted(_SAMPLE_DATA.glob("*.ang"))

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
        if (ref_dir / stem / f).is_file():
            files.append(f)

    return files


@pytest.fixture(scope="session")
def reference_results():

    results_dir = CACHE_DIR / "reference"
    os.makedirs(results_dir, exist_ok=True)

    for file in _TEST_FILES:
        key = file.stem
        os.makedirs(results_dir / key, exist_ok=True)

        if not os.path.isfile(results_dir / f"{key}/{key}.dream3d"):
            # fmt: off
            subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{file.parent}:/data",
                    "-v", f"{results_dir / key}:/results",
                    "--user", f"{os.getuid()}:{os.getgid()}",
                    "ghcr.io/uomresearchit/cold-dwell-fatigue-of-titanium-alloys:v0.3.0-cli",
                    "-o", "/results",
                    "--stress-axis", ARGS["stress_axis"],
                    "--min-mtr-size", str(ARGS["min_mtr_size"]),
                    f"/data/{file.name}",
                ],
                check=True,
            )
            # fmt: on

            # Move post-processing results to analysis subfolder
            for f in _ANALYSIS_FILES:
                if os.path.isfile(results_dir / key / f):
                    d = (results_dir / key / "analysis" / f).parent
                    os.makedirs(d, exist_ok=True)
                    shutil.move(
                        results_dir / key / f, results_dir / key / "analysis" / f
                    )
                    if not os.listdir(d):
                        shutil.rmtree(d)

            for d in os.listdir(results_dir):
                if os.path.isdir(d) and not os.listdir(d):
                    shutil.rmtree(d)

    yield results_dir


@pytest.mark.parametrize("test_file", _TEST_FILES, ids=lambda p: p.stem)
def test_reference_available(reference_results, test_file):
    """Check that the expected results files have been generated"""

    stem = test_file.stem
    for relpath in expected_files(stem):
        path = reference_results / stem / relpath
        assert path.is_file(), f"Expected file not found: {path}"
        assert os.path.getsize(path) > 0, f"File is empty: {path}"


@pytest.fixture(params=_TEST_FILES, ids=lambda p: p.stem, scope="module")
def current_results(request):

    from microtexture.cli import parse_args, main

    test_file = request.param
    results_dir = CACHE_DIR / "results" / test_file.stem
    if results_dir.is_dir():
        shutil.rmtree(results_dir)
    os.makedirs(results_dir, exist_ok=True)

    # fmt: off
    args = parse_args([
        "-o", str(results_dir),
        "--stress-axis", ARGS["stress_axis"],
        "--min-mtr-size", str(ARGS["min_mtr_size"]),
        "--no-analysis",
        str(test_file),
    ])
    # fmt: on

    main(args)

    yield results_dir


def test_current(reference_results, current_results):
    """Check that the expected results files have been generated"""

    for filename in expected_files(current_results.name, reference_results):
        path = current_results / filename
        assert path.is_file(), f"Expected file not found: {path}"
        assert os.path.getsize(path) > 0, f"File is empty: {path}"


def test_analysis(reference_results, current_results):

    from microtexture.postprocess import analyzeData

    stem = current_results.name
    analysis_dir = current_results / "analysis"
    if analysis_dir.is_dir():
        shutil.rmtree(analysis_dir)
    os.makedirs(analysis_dir, exist_ok=True)

    dream3d_file = current_results / f"{stem}.dream3d"
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

    summary_file = analysis_dir / "Microtexture_Statistics_Summary.md"
    ref_summary = (
        reference_results / f"{stem}/analysis/Microtexture_Statistics_Summary.md"
    )
    compare_summaries(ref_summary, summary_file)


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


def compare_summaries(reference_summary, generated_summary):

    ref_tables = read_summary(reference_summary)
    gen_tables = read_summary(generated_summary)

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
