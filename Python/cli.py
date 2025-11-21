"""
Command-line interface replacement for the old Tk GUI.
"""

import os
from warnings import warn
import json
from argparse import Namespace, ArgumentParser
import subprocess

from jinja2 import Environment, FileSystemLoader

from config import Config


def main():
    args = parse_args()
    render_template(args.template_path, vars(args), args.json_path)

    if not args.no_run and args.runner_path:
        run_pipeline(args.json_path, runner_path=args.runner_path)


def render_template(template_name: str, context: dict, json_path: str) -> dict:
    """Render a json.Jinja template and save to json_path"""
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(template_name)),
        keep_trailing_newline=True,
        autoescape=False,
    )
    tpl = env.get_template(os.path.basename(template_name))
    rendered = tpl.render(**context)

    # Debug: print rendered template
    with open("debug_rendered_template.json", "w", encoding="utf8") as f:
        f.write(rendered)

    # validate JSON before writing
    j = json.loads(rendered)

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf8") as f:
        json.dump(j, f, indent=4)

    print(f"Generated JSON input file: {json_path}")


def run_pipeline(json_path: str, runner_path: str):
    """Run the DREAM3D PipelineRunner with the given JSON input file"""

    if not os.path.isfile(runner_path):
        raise FileNotFoundError(f"PipelineRunner not found or invalid: {runner_path}")
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"JSON input file not found or invalid: {json_path}")

    cmd = [runner_path, "-p", json_path]
    status = subprocess.run(cmd, capture_output=True)

    if status.returncode == 0:
        print(f"PipelineRunner executed successfully for: {json_path}")
    else:
        print(f"PipelineRunner failed for: {json_path}")
        print("STDOUT:")
        print(status.stdout.decode())
        print("STDERR:")
        print(status.stderr.decode())


def parse_args() -> Namespace:

    cfg = Config()

    p = ArgumentParser(description="CLI for executing Dream3D pipeline templates")
    p.add_argument("-f", "--input-file", help="Path to a single .ang or .ctf file")
    p.add_argument(
        "-o",
        "--output-dir",
        default=r"Results/{basename}",
        help="Results (sub)directory ['%(default)s']. {basename} will be replaced by "
             "the input file name without extension.",
    )

    ang = p.add_argument_group("cleanup parameters for .ang files")
    ang._extension = "ang"  # see check_explicit_args
    ang.add_argument(
        "--ci-mask-threshold",
        type=float,
        default=0.05,
        help="Confidence Index (CI) Threshold for Good Data [%(default)s]",
    )
    ang.add_argument(
        "--iq-mask-threshold",
        type=float,
        default=20000.0,
        help="Image Quality (IQ) Threshold for Good Data [%(default)s]",
    )
    ang.add_argument(
        "--ci-primary-threshold",
        type=float,
        default=0.05,
        help="Primary Cleanup CI Threshold [%(default)s]",
    )
    ang.add_argument(
        "--ci-secondary-threshold",
        type=float,
        default=0.1,
        help="Secondary Cleanup CI Threshold [%(default)s]",
    )

    ctf = p.add_argument_group("cleanup parameters for .ctf files")
    ctf._extension = "ctf"  # see check_explicit_args
    ctf.add_argument(
        "--error-mask-threshold",
        type=int,
        default=1,
        help="Confidence Index (CI) Threshold for Good Data [%(default)s]",
    )
    ctf.add_argument(
        "--bc-primary-threshold",
        type=float,
        default=30,
        help="Primary Cleanup Band Contrast (BC) Threshold [%(default)s]",
    )
    ctf.add_argument(
        "--bc-secondary-threshold",
        type=float,
        default=50,
        help="Secondary Cleanup BC Threshold [%(default)s]",
    )

    p.add_argument_group("Analysis parameters")
    p.add_argument(
        "--caxis-misalignment",
        type=int,
        default=20,
        help="C-Axis Misalignment Threshold (deg) for Pixel Segmentation [%(default)s]",
    )
    p.add_argument(
        "--min-mtr-size",
        type=float,
        default=10000,
        help="Minimum MTR Size, um^2 [%(default)s]",
    )
    p.add_argument(
        "--stress-axis",
        choices=["100", "010", "001"],
        default="001",
        help="Stress axis direction (x='100', y='010', z='001') ['%(default)s']",
    )

    d3d = p.add_argument_group("DREAM3D execution")
    d3d.add_argument(
        "--version", default=cfg.dream3d_version, help="DREAM3D version ['%(default)s']"
    )
    d3d.add_argument(
        "--template-path",
        default=cfg._dream3d_pipeline_template,
        help="Path to DREAM3D pipeline template ['%(default)s']. "
             "{EXT} and {ext} tokens will be replaced by the (upper / lower case) "
             "input file extension.",
    )
    d3d.add_argument(
        "--no-run",
        action="store_true",
        help="Do not attempt to run PipelineRunner or analysis, just generate JSON file.",
    )
    d3d.add_argument(
        "--runner-path",
        default=cfg.dream3d_pipeline_runner,
        help="Path to DREAM3D PipelineRunner [%(default)s]",
    )

    args = p.parse_args()

    if not os.path.isfile(args.input_file):
        raise FileNotFoundError(f"Input file {args.input_file} does not exist.")

    ext = os.path.splitext(args.input_file)[1].lower().strip(".")
    args.extension = ext

    if ext not in ["ang", "ctf"]:
        raise ValueError(f"Input file must be .ang or .ctf; got .{ext}.")

    _check_explicit_args(p, ext)

    args.template_path = args.template_path.format(EXT=ext.upper(), ext=ext.lower())
    if not os.path.isfile(args.template_path):
        raise FileNotFoundError(f"Template file {args.template_path} does not exist.")

    basename = os.path.basename(args.input_file).rsplit(".", 1)[0]
    args.basename = basename

    args.output_dir = args.output_dir.format(basename=basename)
    args.json_path = os.path.join(args.output_dir, basename + ".json")

    if not args.no_run and not os.path.isfile(args.runner_path):
        raise FileNotFoundError(
            f"DREAM3D PipelineRunner not found at: {args.runner_path}"
        )

    return args


def _check_explicit_args(
    parser: ArgumentParser,
    ext: str,
):
    """
    Warn about explicit arguments that don't match the input file extension

    Arguments that are specific to one file type are expected to be grouped
    in an ArgumentGroup with an '_extension' attribute
    """

    # Get a dict {ext: set(arguments)} for argument groups tagged with an _extension
    groups = {
        g._extension: {a.dest for a in g._group_actions}
        for g in parser._action_groups
        if getattr(g, "_extension", None)
    }

    explicit = _explicit_args(parser)
    own = groups.get(ext, set())

    for e, v in groups.items():
        if e == ext:
            continue
        weird = [a for a in v if getattr(explicit, a) and a not in own]
        if any(weird):
            warn(f"{e}-specific arguments provided but input file is .{ext}; ignoring.")


def _explicit_args(parser: ArgumentParser) -> Namespace:
    """\
    Check which arguments were explicitly provided
    Source: Elliot Way @ https://stackoverflow.com/a/69229790
    """

    class _Sentinel:
        pass

    names = {a.dest for a in parser._actions}

    sentinel = _Sentinel()
    sentinel_ns = Namespace(**{k: sentinel for k in names})
    parser.parse_args(namespace=sentinel_ns)
    explicit = Namespace(
        **{k: (v is not sentinel) for k, v in vars(sentinel_ns).items()}
    )
    return explicit


if __name__ == "__main__":
    main()
