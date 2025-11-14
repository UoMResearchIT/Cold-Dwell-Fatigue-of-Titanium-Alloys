"""Create Jinja2 templates from the existing JSON Dream3D pipeline templates.

This script reads the JSON files in ../Templates/ and writes .j2 copies where
certain keys are replaced with Jinja placeholders.

Run this once to produce the .j2 files used by `utils_cli.py`.
"""

import json
import os

TEMPLATES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "Templates")
)

MAPPINGS = {
    "PW_ANG_routine_v65.json": {
        # JSON path (as tuple of keys) -> jinja variable name
        ("00", "InputFile"): "input_file",
        ("08", "SelectedThresholds", 0, "Comparison Value"): "mask1_value",
        ("08", "SelectedThresholds", 1, "Comparison Value"): "mask2_value",
        ("13", "MinConfidence"): "primary_cleanup_value",
        ("14", "MinConfidence"): "secondary_cleanup_value",
        ("16", "MisorientationTolerance"): "caxis_misalignment",
        ("09", "OutputPath"): "initial_pole_figure",
        ("44", "OutputPath"): "final_pole_figure",
        ("45", "OutputPath"): "mtr_pole_figure",
        ("40", "SelectedThresholds", 0, "Comparison Value"): "min_mtr_size",
        ("46", "FileName"): "raw_ipf_z",
        ("47", "FileName"): "cleaned_ipf_z",
        ("48", "FileName"): "average_ipf_z",
        ("49", "FileName"): "mtr_ipf_z",
        ("50", "OutputFile"): "dream3d_output",
    },
    "PW_CTF_routine_v65.json": {
        ("00", "InputFile"): "input_file",
        ("10", "SelectedThresholds", 0, "Comparison Value"): "mask1_value",
        ("15", "MinConfidence"): "primary_cleanup_value",
        ("16", "MinConfidence"): "secondary_cleanup_value",
        ("18", "MisorientationTolerance"): "caxis_misalignment",
        ("11", "OutputPath"): "initial_pole_figure",
        ("46", "OutputPath"): "final_pole_figure",
        ("47", "OutputPath"): "mtr_pole_figure",
        ("42", "SelectedThresholds", 0, "Comparison Value"): "min_mtr_size",
        ("48", "FileName"): "raw_ipf_z",
        ("49", "FileName"): "cleaned_ipf_z",
        ("50", "FileName"): "average_ipf_z",
        ("51", "FileName"): "mtr_ipf_z",
        ("52", "OutputFile"): "dream3d_output",
    },
}


def set_nested(data, path, value):
    """Set a nested value given a path tuple, creating lists/dicts as needed."""
    cur = data
    for i, key in enumerate(path):
        last = i == len(path) - 1
        if isinstance(key, int):
            # ensure cur is a list
            if not isinstance(cur, list):
                raise TypeError(f"Expected list at path {path[:i]}, got {type(cur)}")
            # extend list if needed
            while key >= len(cur):
                cur.append(None)
            if last:
                cur[key] = value
            else:
                if cur[key] is None:
                    # decide next container type: if next key is int -> list else dict
                    next_key = path[i + 1]
                    cur[key] = [] if isinstance(next_key, int) else {}
                cur = cur[key]
        else:
            if last:
                cur[key] = value
            else:
                if key not in cur or cur[key] is None:
                    next_key = path[i + 1]
                    cur[key] = [] if isinstance(next_key, int) else {}
                cur = cur[key]


def create_template(src_filename, mapping):
    src_path = os.path.join(TEMPLATES_DIR, src_filename)
    if not os.path.exists(src_path):
        print(f"Source template not found: {src_path}")
        return

    with open(src_path, "r", encoding="utf8") as f:
        raw = f.read()

    # Load JSON to python structure
    data = json.loads(raw)

    # Apply mappings to insert jinja placeholders
    for path, varname in mapping.items():
        # insert placeholder string
        placeholder = f"{{{{ {varname} }}}}"
        set_nested(data, path, placeholder)

    out_filename = src_filename.replace(".json", ".j2")
    out_path = os.path.join(TEMPLATES_DIR, out_filename)
    with open(out_path, "w", encoding="utf8") as f:
        # Dump JSON with indentation, but keep placeholders as raw strings
        json.dump(data, f, indent=4)

    print(f"Wrote Jinja template: {out_path}")


def main():
    for fname, mapping in MAPPINGS.items():
        create_template(fname, mapping)


if __name__ == "__main__":
    main()
