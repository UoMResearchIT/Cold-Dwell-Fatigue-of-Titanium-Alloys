#! /usr/bin/env python
"""
Generates summary plots and statistics after running a Dream3D pipeline
(Stand-alone version of forms.analyzeData + required utils)
"""

import sys
import os
from typing import Literal
from configargparse import ArgumentParser, Namespace, YAMLConfigFileParser
import warnings
import numpy as np
from pandas import DataFrame, cut, ExcelWriter
import h5py
from skimage.measure import regionprops
from PIL.Image import fromarray
from PIL.ImageFont import truetype
from PIL.ImageDraw import Draw
from matplotlib.pyplot import get_cmap
from matplotlib.colors import to_rgb
from skimage.segmentation import mark_boundaries
from imageio import imsave


def analyzeData(
    dream3d_file: str = None,
    output_dir: str = None,
    stress_axis: Literal["001", "010", "001"] = "001",
    min_mtr_size: int = 10000,
):

    if not dream3d_file or not os.path.isfile(dream3d_file):
        raise FileNotFoundError("Failed to find dream3d file at: {pattern}")

    if output_dir is None:
        output_dir = os.path.dirname(dream3d_file)
    assert os.path.isdir(output_dir)

    assert stress_axis in ("001", "010", "001")
    ref_dir = list(map(int, stress_axis))

    print(f"Processing {dream3d_file}")
    d3d = read_dream3d_file(dream3d_file, ref_dir=ref_dir, mtr_size=min_mtr_size)

    # Generate and save MTR ID Map
    mtr_id_map = array2rgb(d3d["mtr_id_map"], cmap="nipy_spectral")
    mtr_id_map_w_boundaries = (
        mark_boundaries(mtr_id_map, d3d["mtr_id_map"], color=(1, 1, 1), mode="inner")
        * 255
    ).astype("uint8")
    mtr_id_map_with_scalebar = add_scalebar(
        d3d=None,
        rgb_image=mtr_id_map_w_boundaries,
        stepsize=d3d["stepsize"],
        plot=False,
    )
    imsave(
        os.path.join(output_dir, "Individual_MTRs.png"),
        np.array(mtr_id_map_with_scalebar),
    )

    # Generate and Save IPF Images with Scalebar
    for ref in ["x", "y", "z"]:

        subdir = os.path.join(output_dir, "IPF_Images", ref.upper())
        os.makedirs(subdir, exist_ok=True)

        ipf_with_scalebar = add_scalebar(
            d3d=None,
            rgb_image=d3d[f"ipf_cleaned_{ref.lower()}"],
            stepsize=d3d["stepsize"],
            plot=False,
        )
        imsave(
            os.path.join(
                subdir,
                f"IPF_Cleaned_{ref.upper()}_Image_w_Scalebar.png",
            ),
            ipf_with_scalebar,
        )

        mtr_ipf_with_scalebar = add_scalebar(
            d3d=None,
            rgb_image=d3d[f"ipf_mtr_{ref.lower()}"],
            stepsize=d3d["stepsize"],
            plot=False,
        )
        imsave(
            os.path.join(
                subdir,
                f"IPF_MTR_{ref.upper()}_Image_w_Scalebar.png",
            ),
            mtr_ipf_with_scalebar,
        )

    # Load Raw Data and Add to Single Dataframe
    raw_data = DataFrame(
        data=np.c_[
            d3d["mtr_sizes"],
            d3d["mtr_caxis_misalignments"],
            d3d["mtr_misorientations"],
            d3d["mtr_solidity"],
            d3d["mtr_intensity"],
            d3d["mtr_aspect_ratios"],
        ],
        columns=[
            "MTR Area, um^2",
            "MTR Caxis Misalignment, deg",
            "MTR Misorientation, deg",
            "Solidity",
            "MTR Intensity",
            "MTR Aspect Ratio",
        ],
    )
    raw_data.insert(0, "MTR Class", d3d["mtr_class"])
    raw_data.insert(0, "Sample", d3d["fname"])

    if raw_data.size == 0:
        warnings.warn("No MTRs identified using current settings")
        return

    raw_data.replace([np.inf, -np.inf], np.nan, inplace=True)
    raw_data.dropna(inplace=True)

    raw_data_output_path = os.path.join(output_dir, "Raw_Data.csv")
    raw_data.to_csv(raw_data_output_path)

    # Get Groups by Scan and MTR Class
    grps = raw_data.groupby(["Sample", "MTR Class"])

    # Calculate Descriptive Statistics
    stats = grps.describe()

    # Calculate Area Fraction
    stats2 = grps.agg(Total_Area_um2=("MTR Area, um^2", "sum")).reset_index()
    stats2["Area Fraction"] = stats2.apply(
        lambda x: x["Total_Area_um2"] / 1000**2 / d3d["scan_area_mm2"],
        axis=1,
    )

    # Calculate Number Density
    counts = grps.agg(Count=("MTR Area, um^2", len)).reset_index()
    stats2["Count"] = counts["Count"]
    stats2["Number Density (Qty/mm)"] = counts.apply(
        lambda x: x["Count"] / d3d["scan_area_mm2"], axis=1
    )

    scan_areas = DataFrame(
        {
            "Scan Area, mm2": [d3d["scan_area_mm2"]],
            "Pixel Fraction Altered By Cleanup": [
                d3d["pixel_fraction_altered_by_cleanup"]
            ],
        },
        index=[d3d["fname"]],
    )

    # Save Summary Statistics to Results Folder
    output_path = os.path.join(output_dir, "Microtexture_Statistics_Summary.xlsx")

    writer = ExcelWriter(output_path)

    # Unroll Multi-index columns and write each dataset to its own tab
    columns = np.unique([n[0] for n in stats.columns])

    for col in columns:
        stats = stats.rename(columns={"count": "number_of_mtrs"})
        stats[col].to_excel(writer, sheet_name=col, float_format="%.4f")

    stats2.to_excel(writer, sheet_name="Area Fractions", float_format="%.4f")
    scan_areas.to_excel(
        writer, sheet_name="Scan Areas and Cleanup Summary", float_format="%.4f"
    )
    writer.close()

    print("Program has completed successfully")


def array2rgb(arr, cmap="jet", vmin=0, vmax=1, nan_color="k"):
    """
    Takes a 2d array and colormap name, scales the input, and returns a RGB uint8 array
    """
    scaled = (arr - np.nanmin(arr)) / (np.nanmax(arr) - np.nanmin(arr))
    scaled = scaled * (vmax - vmin) + vmin
    cmap = get_cmap(cmap)
    rgb = cmap(scaled, bytes=True)[:, :, :3]
    rgb[np.isnan(scaled)] = np.array(to_rgb(nan_color), dtype="uint8") * 255
    return rgb


def calc_misalignment(hkl, ref_dir=[0, 0, 1]):
    """
    Calculates misalignment angle in deg between ref_dir and hkl
    """
    # Project to single hemisphere
    ref_dir = np.array(ref_dir)
    dotproduct = np.dot(hkl, ref_dir)

    magA = np.sqrt(np.sum(ref_dir**2, axis=0))
    magB = np.sqrt(np.sum(hkl**2, axis=1))
    mtr_caxis = (
        180 / np.pi * np.arccos(dotproduct / (magA * magB))
    )  # %misalignment of every feature relative to stress axis
    mtr_caxis[mtr_caxis > 90] = 180 - mtr_caxis[mtr_caxis > 90]

    return mtr_caxis


def getRegionProp(grainID_map, prop="solidity"):
    props = []
    label = []
    for region in regionprops(grainID_map):
        label.append(region.label)
        props.append(region[prop])
    df = DataFrame(label, columns=["Label"])
    df[prop] = props
    df = df.set_index("Label")
    return df


def read_dream3d_file(d3d, ref_dir=[0, 0, 1], mtr_size=10000):
    data = h5py.File(d3d, "r")
    d = {}
    d["fname"] = os.path.basename(d3d).split(".dream3d")[0]
    d["eulers"] = data["DataContainers/ImageDataContainer/CellFeatureData/AvgEuler"][1:]
    d["phases"] = data["DataContainers/ImageDataContainer/CellFeatureData/Phases"][1:]
    d["num_neighbors"] = data[
        "DataContainers/ImageDataContainer/CellFeatureData/NumNeighbors2"
    ][1:]
    d["sizes"] = data[
        "DataContainers/ImageDataContainer/CellFeatureData/EquivalentDiameters"
    ][1:]
    try:
        d["neighbor_list"] = data[
            "DataContainers/ImageDataContainer/CellFeatureData/NeighborList2"
        ][:].tolist()
        d["shared_surfaces"] = data[
            "DataContainers/ImageDataContainer/CellFeatureData/SharedSurfaceAreaList2"
        ][:].tolist()
    except:
        pass
    d["avg_caxis"] = data["DataContainers/ImageDataContainer/CellFeatureData/AvgCAxes"][
        1:
    ]
    d["mask"] = data["DataContainers/ImageDataContainer/CellData/Mask"][0, :, :, 0]

    try:
        d["raw_caxis"] = data["DataContainers/ImageDataContainer/CellData/Raw_CAxes"][0]
        d["caxis_misalignments"] = calc_misalignment(
            d["raw_caxis"].reshape(-1, 3), ref_dir=ref_dir
        ).reshape(d["raw_caxis"].shape[:2])

    except:
        pass

    d["cells"] = data["/DataContainers/ImageDataContainer/CellFeatureData/NumCells"][
        1:
    ].ravel()

    d["volumes"] = data["DataContainers/ImageDataContainer/CellFeatureData/Volumes"][
        1:
    ].ravel()
    d["centroids"] = data[
        "DataContainers/ImageDataContainer/CellFeatureData/Centroids"
    ][1:]
    d["misorientation"] = data[
        "DataContainers/ImageDataContainer/CellFeatureData/FeatureAvgCAxisMisorientations"
    ][1:].ravel()
    d["grainIDs"] = data["/DataContainers/ImageDataContainer/CellData/MTRIds"][
        0, :, :, 0
    ]

    # IPF Z Direction
    d["ipf_raw_z"] = data["DataContainers/ImageDataContainer/CellData/IPF_Raw_Z"][
        0
    ]  # shape (1, 1000, 1001, 3)
    d["ipf_cleaned_z"] = data[
        "DataContainers/ImageDataContainer/CellData/IPF_Cleaned_Z"
    ][
        0
    ]  # shape (1, 1000, 1001, 3)
    d["ipf_avg_z"] = data["DataContainers/ImageDataContainer/CellData/IPF_Average_Z"][
        0
    ]  # shape (1, 1000, 1001, 3)
    d["ipf_mtr_z"] = data["DataContainers/ImageDataContainer/CellData/IPF_MTR_Z"][
        0
    ]  # shape (1, 1000, 1001, 3)

    # IPF Y Direction
    d["ipf_raw_y"] = data["DataContainers/ImageDataContainer/CellData/IPF_Raw_Y"][
        0
    ]  # shape (1, 1000, 1001, 3)
    d["ipf_cleaned_y"] = data[
        "DataContainers/ImageDataContainer/CellData/IPF_Cleaned_Y"
    ][
        0
    ]  # shape (1, 1000, 1001, 3)
    d["ipf_avg_y"] = data["DataContainers/ImageDataContainer/CellData/IPF_Average_Y"][
        0
    ]  # shape (1, 1000, 1001, 3)
    d["ipf_mtr_y"] = data["DataContainers/ImageDataContainer/CellData/IPF_MTR_Y"][
        0
    ]  # shape (1, 1000, 1001, 3)

    # IPF X Direction
    d["ipf_raw_x"] = data["DataContainers/ImageDataContainer/CellData/IPF_Raw_X"][
        0
    ]  # shape (1, 1000, 1001, 3)
    d["ipf_cleaned_x"] = data[
        "DataContainers/ImageDataContainer/CellData/IPF_Cleaned_X"
    ][
        0
    ]  # shape (1, 1000, 1001, 3)
    d["ipf_avg_x"] = data["DataContainers/ImageDataContainer/CellData/IPF_Average_X"][
        0
    ]  # shape (1, 1000, 1001, 3)
    d["ipf_mtr_x"] = data["DataContainers/ImageDataContainer/CellData/IPF_MTR_X"][
        0
    ]  # shape (1, 1000, 1001, 3)

    d["raw_eulers"] = data["DataContainers/ImageDataContainer/CellData/EulerAngles"][
        0
    ]  # shape (1, 1000, 1001, 3)
    d["avg_eulers"] = data["DataContainers/ImageDataContainer/CellData/AvgEulerAngles"][
        0
    ]  # shape (1, 1000, 1001, 3)
    d["twist_angles"] = np.abs(d["eulers"][:, -1] * 180 / np.pi) % 30

    ind = np.where(d["volumes"] >= mtr_size)[0]
    d["Number_MTRS"] = len(ind)
    d["mtr_sizes"] = d["volumes"][ind]
    d["mtr_circle_diameters_um"] = np.sqrt(
        4 * d["mtr_sizes"] / np.pi
    )  # A = pi*r**2  --> D = sqrt(4*A/pi)

    d["mtr_misorientations"] = d["misorientation"][ind]
    d["mtr_caxis_misalignments"] = calc_misalignment(
        d["avg_caxis"][ind].reshape(-1, 3), ref_dir=ref_dir
    )

    bins = [0, 25, 40, 60, 70, 100]
    labels = ["Hard", "Misc", "Initiator", "Misc", "Soft"]
    df = DataFrame({"misalignment": d["mtr_caxis_misalignments"]})
    mtr_class = (
        cut(df["misalignment"], bins, labels=False)
        .map({i: x for i, x in enumerate(labels)})
        .values.tolist()
    )
    d["mtr_class"] = mtr_class

    mtr_ind = ind + 1
    mtr_mask = np.isin(d["grainIDs"], mtr_ind)
    mtr_ids = d["grainIDs"].copy()
    mtr_ids[~mtr_mask] = 0
    d["mtr_mask"] = mtr_mask
    d["mtr_id_map"] = mtr_ids

    minor_axis_length = getRegionProp(mtr_ids, prop="minor_axis_length")
    major_axis_length = getRegionProp(mtr_ids, prop="major_axis_length")
    mtr_aspect_ratios = (
        major_axis_length["major_axis_length"] / minor_axis_length["minor_axis_length"]
    )
    d["mtr_aspect_ratios"] = mtr_aspect_ratios

    solidity = getRegionProp(mtr_ids, prop="solidity")
    solidity = solidity["solidity"].values
    d["mtr_solidity"] = solidity
    d["mtr_intensity"] = (
        d["mtr_sizes"]
        * solidity
        * np.cos(d["mtr_caxis_misalignments"] * np.pi / 180)
        / d["mtr_misorientations"]
        / 1e4
    )

    mtr_ipf = d["ipf_cleaned_z"].copy()
    mtr_ipf[~mtr_mask] = 0
    d["mtr_ipf"] = mtr_ipf
    d["stepsize"] = np.sqrt(np.mean(d["volumes"] / d["cells"]))

    ind = np.sum(d["ipf_cleaned_z"], axis=2) > 0
    scan_area_pct = np.sum(ind.astype("uint8")) / (float(ind.shape[0]) * ind.shape[1])
    dim1, dim2 = (
        d["ipf_cleaned_z"].shape[0] * d["stepsize"] / 1000.0,
        d["ipf_cleaned_z"].shape[1] * d["stepsize"] / 1000.0,
    )
    area = scan_area_pct * dim1 * dim2
    d["scan_area_mm2"] = area

    # Calculate fraction alterred
    elemwise_check = d["ipf_cleaned_z"] == d["ipf_raw_z"]
    elemwise_delta = np.all(elemwise_check, axis=-1)
    d["pixel_fraction_altered_by_cleanup"] = (
        elemwise_delta.size - elemwise_delta.sum()
    ) / elemwise_delta.size

    return d


def create_cpm_cmap(d3d, reference_frame="HKL", reference_direction="001"):
    caxis = np.abs(d3d["raw_caxis"])
    cmap = np.empty_like(caxis).astype("uint8")

    if reference_frame == "TSL":
        if reference_direction == "001":
            cmap[:, :, 0] = (caxis[:, :, 2] * 255).astype("uint8")  # R
            cmap[:, :, 1] = (caxis[:, :, 0] * 255).astype("uint8")  # G
            cmap[:, :, 2] = (caxis[:, :, 1] * 255).astype("uint8")  # B
        elif reference_direction == "010":
            cmap[:, :, 0] = (caxis[:, :, 1] * 255).astype("uint8")  # B
            cmap[:, :, 1] = (caxis[:, :, 2] * 255).astype("uint8")  # R
            cmap[:, :, 2] = (caxis[:, :, 0] * 255).astype("uint8")  # G
        elif reference_direction == "100":
            cmap[:, :, 0] = (caxis[:, :, 0] * 255).astype("uint8")  # B
            cmap[:, :, 1] = (caxis[:, :, 1] * 255).astype("uint8")  # R
            cmap[:, :, 2] = (caxis[:, :, 2] * 255).astype("uint8")  # G

    elif reference_frame == "HKL":
        if reference_direction == "001":
            cmap[:, :, 0] = (caxis[:, :, 2] * 255).astype("uint8")  # R
            cmap[:, :, 1] = (caxis[:, :, 0] * 255).astype("uint8")  # G
            cmap[:, :, 2] = (caxis[:, :, 1] * 255).astype("uint8")  # B
        elif reference_direction == "100":
            cmap[:, :, 0] = (caxis[:, :, 1] * 255).astype("uint8")  # B
            cmap[:, :, 1] = (caxis[:, :, 2] * 255).astype("uint8")  # R
            cmap[:, :, 2] = (caxis[:, :, 0] * 255).astype("uint8")  # G
        elif reference_direction == "010":
            cmap[:, :, 0] = (caxis[:, :, 0] * 255).astype("uint8")  # B
            cmap[:, :, 1] = (caxis[:, :, 1] * 255).astype("uint8")  # R
            cmap[:, :, 2] = (caxis[:, :, 2] * 255).astype("uint8")  # G

    cmap[~d3d["mask"].astype("bool")] = [0, 0, 0]
    return cmap


def add_scalebar(d3d=None, length_pct=0.25, plot=False, rgb_image=None, stepsize=None):
    """
    If a d3d data dictionary is provided, the script will read the IPF image and add a scalebar automatically based on stepsize
    Otherwise, if an rgb_image and stepsize (um_per_px) are provided and d3d=None, then it will use the manually provided inputs
    """

    # Crop off bottom to remove scalebar
    if sys.platform == "linux":
        font_name = "DejaVuSans"
    else:
        font_name = "arial"
    # colors = ["black"]
    units = ["mm"]

    if isinstance(d3d, dict):
        rgb_image = fromarray(d3d["ipf_cleaned_z"].copy())
        stepsize = d3d["stepsize"]  # um_per_px

    elif isinstance(rgb_image, np.ndarray) and np.isreal(stepsize):
        rgb_image = fromarray(rgb_image).copy()

    w, h = rgb_image.size

    # assign font, size, color
    fontsize = np.floor(0.03 * h).astype("int32")
    font = truetype(font_name, size=fontsize)
    # fill = np.random.choice(colors)

    # assign length
    length = int(w * length_pct)
    actual_length_um = length * stepsize
    rounded_length_um = np.ceil(actual_length_um)
    length = rounded_length_um / stepsize
    thickness = int(0.025 * h)

    # assign text on top or bottom of scale bar
    # top = True

    # random location 15% of the time other bottom right quadrant. if text is going on bottom, increase bottom buffer size
    right_buffer = int(0.05 * w)  # 50
    bottom_buffer = int(0.05 * h)  # 50

    # get rectangle parameters
    rect_width = int(0.025 * h)
    # outline_color = fill
    # rect_fill = (255, 255, 255, 255)

    # Determine offset from scalebar
    offset = -1.05 * bottom_buffer  # -55

    xs = w - right_buffer - length
    xf = xs + length

    ys = h - bottom_buffer - rect_width
    xy = ((xs, ys), (xf, ys))
    xy_bg = ((xs * 0.99, ys * 0.94), (xf * 1.01, ys * 1.03))

    # xyrect = ((xs, ys + offset), (xf, ys + offset + rect_width))

    # Locate Center of Line
    # x_center = int(xs + 0.5 * length)

    text_str = "%.3f %s" % (length * stepsize / 1000, units[0])

    # Draw Text and Scalebar
    draw = Draw(rgb_image)
    text_length = draw.textlength(text=text_str, font=font)
    # larger_feature_length = max([text_length, length])
    x_text_center = int(xs + 0.5 * text_length)
    line_center = int(xs + 0.5 * length)
    x_text_offset = line_center - x_text_center

    # Draw Background
    draw.rectangle(xy=xy_bg, fill=(255, 255, 255))
    draw.text(
        xy=(xs + x_text_offset, ys + 1 * offset),
        text=text_str,
        font=font,
        fill=(0, 0, 0),
        align="center",
    )
    draw.line(xy=xy, width=thickness, fill=(0, 0, 0))

    image_w_scalebar = np.array(rgb_image)

    # if plot:
    #     plt.imshow(image_w_scalebar); plt.pause(.1)

    return image_w_scalebar


def parse_args() -> Namespace:

    def_config_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "defaults.yaml"
    )
    with open(def_config_file, "r") as f:
        cfg = YAMLConfigFileParser().parse(f)

    p = ArgumentParser(
        description="Post-processing of Dream3D pipelines",
        config_file_parser_class=YAMLConfigFileParser,
    )

    p.add_argument('dream3d_file', help="Path to a single .dream3d file (required)")
    p.add_argument("-o", "--output-dir", default=None, help="Results (sub)directory ")

    p.add_argument(
        "--min-mtr-size",
        type=float,
        default=cfg["min_mtr_size"],
        help="Minimum MTR Size, um^2 [%(default)s]",
    )
    p.add_argument(
        "--stress-axis",
        choices=["100", "010", "001"],
        default=cfg["stress_axis"],
        help="Stress axis direction (x='100', y='010', z='001') ['%(default)s']",
    )

    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    args.dream3d_file = os.path.abspath(os.path.expanduser(os.path.expandvars(args.dream3d_file)))
    if args.output_dir:
        args.output_dir = os.path.expanduser(os.path.expandvars(args.output_dir))

    if args.verbose:
        print("Parsed Inputs:")
        [print(f"\t{k}: {v}") for k, v in vars(args).items()]

    return args


if __name__ == "__main__":
    args = parse_args()
    analyzeData(args.dream3d_file, args.output_dir, args.stress_axis, args.min_mtr_size)
