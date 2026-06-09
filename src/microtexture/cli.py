#! /usr/bin/env python
"""
Command-line interface replacement for the old Tk GUI.
"""

import os
import sys
import shutil
from glob import glob
import json
import subprocess
from importlib.resources import files

from configargparse import Namespace, ArgumentParser, YAMLConfigFileParser
from jinja2 import Environment, FileSystemLoader


def main(args: Namespace = None):

    if args is None:
        args = parse_args()
    if args.dry_run:
        print("Dry run: Exiting before JSON generation or pipeline execution.")
        return

    render_template(args.pipeline_template, vars(args), args.json_path)

    if not args.no_runner:
        run_pipeline(args.backend, args.json_path, runner_path=args.pipeline_runner, verbose=args.verbose)

    if not args.no_analysis:

        from .postprocess import analyzeData

        analyzeData(
            dream3d_file=os.path.join(args.output_dir, args.basename + ".dream3d"),
            output_dir=args.output_dir,
            stress_axis=args.stress_axis,
            min_mtr_size=args.min_mtr_size,
            summary_format=args.summary_format,
        )


def render_template(template_name: str, context: dict, json_path: str) -> dict:
    """Render a json.Jinja template and save to json_path"""
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(template_name)),
        keep_trailing_newline=True,
        autoescape=False,
    )
    tpl = env.get_template(os.path.basename(template_name))
    rendered = tpl.render(**context)

    # validate JSON before writing
    j = json.loads(rendered)

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf8") as f:
        json.dump(j, f, indent=4)

    print(f"Generated pipeline file: {json_path}")


def run_pipeline(backend: str, json_path: str, runner_path: str, verbose: bool = False):
    """Run the DREAM3D PipelineRunner/nxrunner with the given JSON input file"""

    if not os.path.isfile(runner_path):
        raise FileNotFoundError(f"DREAM3D runner not found or invalid: {runner_path}")
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"JSON input file not found or invalid: {json_path}")

    cmd = {
        "PipelineRunner": [runner_path, "-p", json_path],
        "nxrunner": [runner_path, "--execute", json_path]
    }[backend]
    status = subprocess.run(cmd, capture_output=not verbose)

    runner = os.path.basename(runner_path) or "DREAM3D runner"
    if status.returncode == 0:
        print(f"{runner} executed successfully for: {json_path}")
    else:
        if not verbose:
            print(f"{runner} STDOUT:")
            print(status.stdout)
            print(f"{runner} STDERR:")
            print(status.stderr)
        raise RuntimeError(f"{runner} failed for: {json_path}")


def parse_args(arg_list: list[str] = None) -> Namespace:

    def_config_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "defaults.yaml"
    )
    with open(def_config_file, "r") as f:
        cfg = YAMLConfigFileParser().parse(f)

    p = ArgumentParser(
        prog="microtexture",
        description="CLI for executing Dream3D pipeline templates",
        config_file_parser_class=YAMLConfigFileParser,
        default_config_files=["./.microtexture", "~/.microtexture"],
    )
    p.add_argument("input_file", help="Path to a single .ang or .ctf file (required)")
    p.add_argument(
        "-c",
        "--config",
        is_config_file=True,
        help=f"Config file path. See {def_config_file} for an example.",
    )
    p.add_argument(
        "-o",
        "--output-dir",
        default=cfg["output-dir"],
        help="Results (sub)directory ['%(default)s']. {basename} will be replaced by "
        "the input file name without extension.",
    )
    p.add_argument(
        "--summary-format",
        choices=["excel", "markdown", "json"],
        action="append",
        nargs="*",
        default=cfg["summary-format"],
        help="Format for summary output file ['%(default)s']",
    )
    p.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Parse arguments and quit",
    )
    p.add_argument(
        "-R",
        "--no-runner",
        action="store_true",
        help="Do not attempt to run PipelineRunner or analysis, just generate JSON file.",
    )
    p.add_argument(
        "-A",
        "--no-analysis",
        action="store_true",
        help="Trigger PipelineRunner, but don't run post-processing analysis",
    )
    p.add_argument(
        "-f",
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in OUTPUT_DIR",
    )
    p.add_argument("-v", "--verbose", action="store_true")

    ang = p.add_argument_group("cleanup parameters for .ang files")
    ang._extension = "ang"  # see check_explicit_args
    ang.add_argument(
        "--ci-mask-threshold",
        type=float,
        default=cfg["ci-mask-threshold"],
        help="Confidence Index (CI) Threshold for Good Data [%(default)s]",
    )
    ang.add_argument(
        "--iq-mask-threshold",
        type=float,
        default=cfg["iq-mask-threshold"],
        help="Image Quality (IQ) Threshold for Good Data [%(default)s]",
    )
    ang.add_argument(
        "--ci-primary-threshold",
        type=float,
        default=cfg["ci-primary-threshold"],
        help="Primary Cleanup CI Threshold [%(default)s]",
    )
    ang.add_argument(
        "--ci-secondary-threshold",
        type=float,
        default=cfg["ci-secondary-threshold"],
        help="Secondary Cleanup CI Threshold [%(default)s]",
    )

    ctf = p.add_argument_group("cleanup parameters for .ctf files")
    ctf._extension = "ctf"  # see check_explicit_args
    ctf.add_argument(
        "--error-mask-threshold",
        type=int,
        default=cfg["error-mask-threshold"],
        help="Confidence Index (CI) Threshold for Good Data [%(default)s]",
    )
    ctf.add_argument(
        "--bc-primary-threshold",
        type=float,
        default=cfg["bc-primary-threshold"],
        help="Primary Cleanup Band Contrast (BC) Threshold [%(default)s]",
    )
    ctf.add_argument(
        "--bc-secondary-threshold",
        type=float,
        default=cfg["bc-secondary-threshold"],
        help="Secondary Cleanup BC Threshold [%(default)s]",
    )

    ana = p.add_argument_group("Analysis parameters")
    ana.add_argument(
        "--caxis-misalignment",
        type=float,
        default=cfg["caxis-misalignment"],
        help="C-Axis Misalignment Threshold (deg) for Pixel Segmentation [%(default)s]",
    )
    ana.add_argument(
        "--min-mtr-size",
        type=float,
        default=cfg["min-mtr-size"],
        help="Minimum MTR Size, um^2 [%(default)s]",
    )
    ana.add_argument(
        "--stress-axis",
        choices=["100", "010", "001"],
        default=cfg["stress-axis"],
        help="Stress axis direction (x='100', y='010', z='001') ['%(default)s']",
    )

    d3d = p.add_argument_group("DREAM3D execution")
    d3d.add_argument(
        "--pipeline-template",
        default=os.getenv("DREAM3D_PIPELINE_TEMPLATE", cfg["pipeline-template"]),
        help="Path to DREAM3D pipeline template ['%(default)s']. "
        "{EXT} and {ext} tokens will be replaced by the (upper / lower case) "
        "input file extension. {microtexture} stands for this package's path. "
        "Override default by setting DREAM3D_PIPELINE_TEMPLATE.",
    )
    d3d.add_argument(
        "--pipeline-runner",
        default=os.getenv("DREAM3D_PIPELINE_RUNNER", cfg["pipeline-runner"]),
        help="Path to DREAM3D PipelineRunner or DREAM3D-NX nxrunner [%(default)s]. "
        "Override default by setting DREAM3D_PIPELINE_RUNNER.",
    )

    args = p.parse_args(arg_list or sys.argv[1:])

    args.input_file = os.path.expanduser(os.path.expandvars(args.input_file))
    if not os.path.isfile(args.input_file):
        candidates = glob(args.input_file)
        if len(candidates) > 1:
            raise ValueError("Cannot yet handle multiple files")
        elif len(candidates) == 0:
            raise FileNotFoundError(f"Input file {args.input_file} does not exist.")
        else:
            args.input_file = candidates[0]
    args.input_file = os.path.abspath(args.input_file)

    ext = os.path.splitext(args.input_file)[1].lower().strip(".")
    args.extension = ext

    if ext not in ["ang", "ctf"]:
        raise ValueError(f"Input file must be .ang or .ctf; got .{ext}.")

    basename = os.path.basename(args.input_file).rsplit(".", 1)[0]
    args.basename = basename

    args.output_dir = args.output_dir.format(basename=basename)
    args.output_dir = os.path.abspath(
        os.path.expanduser(os.path.expandvars(args.output_dir))
    )

    if (
        not args.dry_run and not args.overwrite
        and os.path.isdir(args.output_dir)
        and os.listdir(args.output_dir)
    ):
        raise PermissionError(
            f"Output directory {args.output_dir} exists and is not empty. "
            "Use --overwrite or remove existing files."
        )

    runner = shutil.which(args.pipeline_runner) or ""
    backend = os.path.basename(runner)
    if not args.dry_run and not args.no_runner:
        if not runner:
            raise FileNotFoundError(
                f"DREAM3D/SIMPLNX pipeline-runner ({args.pipeline_runner}) not found"
            )
        if backend not in ["nxrunner", "PipelineRunner"]:
            raise ValueError(
                f"Unrecognized backend, expecting 'nxrunner' of 'PipelineRunner', got {backend}"
            )

    args.pipeline_runner = runner
    args.backend = backend

    args.json_path = os.path.join(
        args.output_dir, basename + (".d3dpipeline" if backend == "nxrunner" else ".json")
    )

    args.pipeline_template = args.pipeline_template.format(
        EXT=ext.upper(),
        ext=ext.lower(),
        microtexture=files("microtexture"),
        suffix = "nx" if backend == "nxrunner" else "v65",
    )

    if not args.dry_run and not args.no_runner and not os.path.isfile(args.pipeline_runner):
        raise FileNotFoundError(
            f"Template file {args.pipeline_template} does not exist."
        )
    
    if args.verbose or args.dry_run:
        print("Parsed Inputs:")
        [print(f"\t{k}: {v}") for k, v in vars(args).items()]

    return args


if __name__ == "__main__":
    main()
