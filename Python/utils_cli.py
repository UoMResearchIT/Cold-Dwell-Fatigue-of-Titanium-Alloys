"""CLI-friendly utilities for generating Dream3D JSON inputs using Jinja2 templates.

This module keeps the original `utils.py` intact and provides an alternative
implementation that uses the Jinja templates produced by
`create_jinja_templates.py`.
"""

import os
import json
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "Templates")
)


def render_template(template_name: str, context: dict) -> dict:
    """Render a Jinja template and return the resulting JSON as a Python dict."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        keep_trailing_newline=True,
        autoescape=False,
    )
    tpl = env.get_template(template_name)
    rendered = tpl.render(**context)
    return json.loads(rendered)


def create_d3d_input_files_v65_ang(input_dictionary, out_dir=None):
    """Generate Dream3D input JSON files for ANG data using the Jinja template.

    input_dictionary should match the structure created by the old GUI code
    (it contains 'paths' mapping with per-sample entries).
    """
    template_name = "PW_ANG_routine_v65.j2"
    if out_dir is None:
        out_dir = os.getcwd()

    for key in input_dictionary["paths"].keys():
        ctx = {
            "input_file": input_dictionary["paths"][key]["input_path"],
            "mask1_value": float(input_dictionary["mask1_value"]),
            "mask2_value": float(input_dictionary["mask2_value"]),
            "primary_cleanup_value": float(input_dictionary["primary_cleanup_value"]),
            "secondary_cleanup_value": float(
                input_dictionary["secondary_cleanup_value"]
            ),
            "caxis_misalignment": int(input_dictionary["caxis_misalignment"]),
            "initial_pole_figure": input_dictionary["paths"][key][
                "initial_pole_figure"
            ],
            "final_pole_figure": input_dictionary["paths"][key]["final_pole_figure"],
            "mtr_pole_figure": input_dictionary["paths"][key]["mtr_pole_figure"],
            "min_mtr_size": float(input_dictionary["min_mtr_size"]),
            "raw_ipf_z": input_dictionary["paths"][key]["raw_ipf_z"],
            "cleaned_ipf_z": input_dictionary["paths"][key]["cleaned_ipf_z"],
            "average_ipf_z": input_dictionary["paths"][key]["average_ipf_z"],
            "mtr_ipf_z": input_dictionary["paths"][key]["mtr_ipf_z"],
            "dream3d_output": input_dictionary["paths"][key]["dream3d"],
        }
        j = render_template(template_name, ctx)
        out_path = input_dictionary["paths"][key]["json_path"]
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf8") as f:
            json.dump(j, f, indent=4)


def create_d3d_input_files_v65_ctf(input_dictionary, out_dir=None):
    """Generate Dream3D input JSON files for CTF data using the Jinja template."""
    template_name = "PW_CTF_routine_v65.j2"
    if out_dir is None:
        out_dir = os.getcwd()

    for key in input_dictionary["paths"].keys():
        ctx = {
            "input_file": input_dictionary["paths"][key]["input_path"],
            "mask1_value": float(input_dictionary["mask1_value"]),
            "primary_cleanup_value": float(input_dictionary["primary_cleanup_value"]),
            "secondary_cleanup_value": float(
                input_dictionary["secondary_cleanup_value"]
            ),
            "caxis_misalignment": int(input_dictionary["caxis_misalignment"]),
            "initial_pole_figure": input_dictionary["paths"][key][
                "initial_pole_figure"
            ],
            "final_pole_figure": input_dictionary["paths"][key]["final_pole_figure"],
            "mtr_pole_figure": input_dictionary["paths"][key]["mtr_pole_figure"],
            "min_mtr_size": float(input_dictionary["min_mtr_size"]),
            "raw_ipf_z": input_dictionary["paths"][key]["raw_ipf_z"],
            "cleaned_ipf_z": input_dictionary["paths"][key]["cleaned_ipf_z"],
            "average_ipf_z": input_dictionary["paths"][key]["average_ipf_z"],
            "mtr_ipf_z": input_dictionary["paths"][key]["mtr_ipf_z"],
            "dream3d_output": input_dictionary["paths"][key]["dream3d"],
        }
        j = render_template(template_name, ctx)
        out_path = input_dictionary["paths"][key]["json_path"]
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf8") as f:
            json.dump(j, f, indent=4)


# small helper to run PipelineRunner on Windows if requested; left intentionally simple
import subprocess


def run_pipelinerunner(json_paths, runner_path=None):
    """Run PipelineRunner.exe for each json path. Runner path must be provided (Windows only).

    On Linux this function will not run anything by default.
    """
    if runner_path is None:
        print("No PipelineRunner path provided; skipping execution.")
        return
    for p in json_paths:
        cmd = [runner_path, "-p", p]
        subprocess.Popen(cmd)
