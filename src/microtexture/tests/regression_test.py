import os
import shutil
import subprocess
from importlib.resources import files

import pandas as pd
import pytest


CACHE_DIR = files("microtexture") / "sample_data/.test"
ARGS = {"stress_axis": "100", "min_mtr_size": 10001}
TOLERANCE = {"relative": 1e-4, "absolute": 1e-6}


@pytest.fixture
def reference_results():

    test_file = files("microtexture") / "sample_data/EBSD_Example_ANG_Public_Domain.ang"
    assert test_file.is_file()

    results_dir = CACHE_DIR / "results"
    os.makedirs(results_dir, exist_ok=True)

    # fmt: off
    if not os.path.isfile(results_dir / "EBSD_Example_ANG_Public_Domain.dream3d"):
        subprocess.run(
            [
                "docker", "run",
                "--rm",
                "-v", f"{test_file.parent}:/data",
                "-v", f"{results_dir}:/results",
                "--user", f"{os.getuid()}:{os.getgid()}",
                "ghcr.io/uomresearchit/cold-dwell-fatigue-of-titanium-alloys:v0.3.0-cli",
                "-o", "/results",
                "--stress-axis", ARGS["stress_axis"],
                "--min-mtr-size", str(ARGS["min_mtr_size"]),
                "--no-analysis",
                f"/data/{test_file.name}",
            ],
            check=True,
        )
    # fmt: on

    yield results_dir


@pytest.fixture
def analysis_results():
    analysis_path = CACHE_DIR / "analysis"
    if analysis_path.is_dir():
        shutil.rmtree(analysis_path)
    os.makedirs(analysis_path, exist_ok=True)
    yield analysis_path


def test_results_available(reference_results):
    """Check that the expected results files have been generated"""

    expected_files = [
        "EBSD_Example_ANG_Public_Domain.dream3d",
        "EBSD_Example_ANG_Public_Domain.json",
        "EBSD_Example_ANG_Public_Domain.xdmf",
        "EBSD_Example_ANG_Public_Domain_IPF_Average_Z.tif",
        "EBSD_Example_ANG_Public_Domain_IPF_Cleaned_Z.tif",
        "EBSD_Example_ANG_Public_Domain_IPF_MTR_Z.tif",
        "EBSD_Example_ANG_Public_Domain_IPF_Raw_Z.tif",
        "PoleFigures/Cleaned_Pole_Figure_Phase_1.pdf",
        "PoleFigures/MTR_Pole_Figure_Phase_1.pdf",
        "PoleFigures/Thresholded_Pole_Figure_Phase_1.pdf",
    ]

    for filename in expected_files:
        assert (reference_results / filename).is_file(), (
            f"Expected file not found: {filename}"
        )


def test_analysis(reference_results, analysis_results):

    from microtexture.postprocess import analyzeData

    analyzeData(
        dream3d_file=reference_results / "EBSD_Example_ANG_Public_Domain.dream3d",
        output_dir=analysis_results,
        stress_axis=ARGS["stress_axis"],
        min_mtr_size=ARGS["min_mtr_size"],
        summary_format=["excel", "markdown", "json"],
    )

    expected_files = [
        "Individual_MTRs.png",
        "Microtexture_Statistics_Summary.xlsx",
        "Microtexture_Statistics_Summary.md",
        "Microtexture_Statistics_Summary.json",
    ]
    for axis in ["X", "Y", "Z"]:
        expected_files.extend(
            [
                f"IPF_Images/{axis}/IPF_Cleaned_{axis}_Image_w_Scalebar.png",
                f"IPF_Images/{axis}/IPF_MTR_{axis}_Image_w_Scalebar.png",
            ]
        )

    for filename in expected_files:
        assert (analysis_results / filename).is_file(), (
            f"Expected file not found: {filename}"
        )

    summary_file = analysis_results / "Microtexture_Statistics_Summary.md"
    reference_summary = files("microtexture") / "sample_data/EBSD_Example_ANG_Summary.md"
    compare_summaries(reference_summary, summary_file)


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
