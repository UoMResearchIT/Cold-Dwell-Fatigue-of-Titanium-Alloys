"""\
Command-line interface replacement for the old Tk GUI.
"""

import os
from warnings import warn

from argparse import Namespace, ArgumentParser

from utils_cli import create_d3d_input_files_v65_ang, create_d3d_input_files_v65_ctf


def parse_args() -> Namespace:
    p = ArgumentParser(
        description="CLI for executing Dream3D pipeline templates"
    )
    p.add_argument("file", nargs=1, help="Path to a single .ang or .ctf file")
    p.add_argument(
        "-o",
        "--output-dir",
        default=r"Results/{basename}",
        help="Results directory [%(default)s]",
    )

    ang = p.add_argument_group("cleanup parameters for .ang files")
    ang.add_argument(
        "--ci-mask",
        type=float,
        default=0.05,
        help="Confidence Index (CI) Threshold for Good Data [%(default)s]",
    )
    ang.add_argument(
        "--iq-mask",
        type=float,
        default=20000.0,
        help="Image Quality (IQ) Threshold for Good Data [%(default)s]",
    )
    ang.add_argument(
        "--ci-primary",
        type=float,
        default=0.05,
        help="Primary Cleanup CI Threshold [%(default)s]",
    )
    ang.add_argument(
        "--ci-secondary",
        type=float,
        default=0.1,
        help="Secondary Cleanup CI Threshold [%(default)s]",
    )

    ctf = p.add_argument_group("cleanup parameters for .ctf files")
    ctf.add_argument(
        "--error-mask",
        type=float,
        default=1,
        help="Confidence Index (CI) Threshold for Good Data [%(default)s]",
    )
    ctf.add_argument(
        "--bc-primary",
        type=float,
        default=30,
        help="Primary Cleanup Band Contrast (BC) Threshold [%(default)s]",
    )
    ctf.add_argument(
        "--bc-secondary",
        type=float,
        default=50,
        help="Secondary Cleanup BC Threshold [%(default)s]",
    )
    p.add_argument_group("Analysis parameters")
    p.add_argument(
        "--caxis",
        type=int,
        default=20,
        help="C-Axis Misalignment Threshold (deg) for Pixel Segmentation [%(default)s]",
    )
    p.add_argument(
        "--min-mtr",
        type=float,
        default=10000,
        help="Minimum MTR Size, um^2 [%(default)s]",
    )
    p.add_argument(
        "--stress-axis",
        choices=["x", "y", "z"],
        default="z",
        help="Stress axis direction [%(default)s]",
    )

    p.add_argument_group("DREAM3D execution")
    p.add_argument("--version", choices=["6.5"], default="6.5")
    p.add_argument(
        "--no-run",
        action="store_true",
        help="Do not attempt to run PipelineRunner afterward",
    )
    p.add_argument("--runner-path", help="Path to DREAM3D PipelineRunner")

    args = p.parse_args()

    # Check which arguments were explicitly provided
    # Source: Elliot Way @ https://stackoverflow.com/a/69229790
    class _Sentinel:
        pass

    sentinel = _Sentinel()
    sentinel_ns = Namespace(**{k: sentinel for k in vars(args)})
    p.parse_args(namespace=sentinel_ns)
    explicit = Namespace(
        **{k: (v is not sentinel) for k, v in vars(sentinel_ns).items()}
    )

    return args, explicit


def build_inputs_from_args(args: Namespace, explicit: Namespace) -> dict:
    """Construct an input_dictionary similar to the GUI's expected shape."""

    if not os.path.isfile(args.file):
        raise FileNotFoundError(f"Input file {args.file} does not exist.")

    ext = os.path.splitext(args.file)[1].lower().strip(".")
    if ext == "ang":
        if any(
            [getattr(explicit, a) for a in ["error_mask", "bc_primary", "bc_secondary"]]
        ):
            warn("CTF-specific arguments provided but input file is .ang; ignoring.")

        mask1 = args.ci_mask
        mask2 = args.iq_mask
        primary = args.ci_primary
        secondary = args.ci_secondary

    elif ext == "ctf":
        if any(
            [getattr(explicit, a) for a in ["iq_mask", "ci_primary", "ci_secondary"]]
        ):
            warn("ANG-specific arguments provided but input file is .ctf; ignoring.")

        mask1 = args.error_mask
        mask2 = None
        primary = args.bc_primary
        secondary = args.bc_secondary
    else:
        raise ValueError(f"Unknown file extension .{ext}; expecting .ang or .ctf")

    basename = os.path.basename(args.file).rsplit(".", 1)[0]

    # stress_axis = {
    #     "x": [1, 0, 0],
    #     "y": [0, 1, 0],
    #     "z": [0, 0, 1],
    # }[args.stress_axis.lower()]

    output_folder = args.output_dir.format(basename=basename)
    os.makedirs(output_folder, exist_ok=True)

    basename = args.basename
    out_json = os.path.join(output_folder, basename + ".json")

    output_file_paths = dict(
        input_path=args.file,
        raw_ipf_z=os.path.join(output_folder, basename + "_IPF_Raw_Z.tif"),
        cleaned_ipf_z=os.path.join(output_folder, basename + "_IPF_Cleaned_Z.tif"),
        average_ipf_z=os.path.join(output_folder, basename + "_IPF_Average_Z.tif"),
        mtr_ipf_z=os.path.join(output_folder, basename + "_IPF_MTR_Z.tif"),
        initial_pole_figure=os.path.join(output_folder, "PoleFigures"),
        final_pole_figure=os.path.join(output_folder, "PoleFigures"),
        mtr_pole_figure=os.path.join(output_folder, "PoleFigures"),
        dream3d=os.path.join(output_folder, basename + ".dream3d"),
        json_path=out_json,
    )

    inputs = dict(
        output_folder_name=args.output_dir,
        caxis_misalignment=str(args.caxis),
        mask1_value=str(mask1),
        mask2_value=str(mask2 or ""),
        primary_cleanup_value=str(primary),
        secondary_cleanup_value=str(secondary),
        min_mtr_size=str(args.min_mtr),
        paths=output_file_paths,
        subdirectories=[os.path.basename(output_folder)],
        parent_directory=os.path.dirname(output_folder),
        extension=ext,
    )

    return inputs


def main():
    args, explicit = parse_args()
    inputs = build_inputs_from_args(args, explicit)

    # use appropriate renderer
    if inputs.extension == "ctf":
        create_d3d_input_files_v65_ctf(inputs)
    else:
        create_d3d_input_files_v65_ang(inputs)

    json_path = inputs["paths"]["json_path"]
    print(f"Generated JSON input file: {json_path}")

    if not args.no_run and args.runner_path:
        from utils_cli import run_pipelinerunner

        run_pipelinerunner(json_path, runner_path=args.runner_path)


if __name__ == "__main__":
    main()
