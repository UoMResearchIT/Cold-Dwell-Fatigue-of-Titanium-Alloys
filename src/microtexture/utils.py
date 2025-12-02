import sys
import glob
import json
import os

import h5py
import numpy as np
from pandas import DataFrame, cut
from skimage.measure import regionprops
from PIL.Image import fromarray
from PIL.ImageFont import truetype
from PIL.ImageDraw import Draw
from matplotlib.pyplot import get_cmap
from matplotlib.colors import to_rgb

from .config import Config


def array2rgb(arr, cmap='jet', vmin=0, vmax=1, nan_color='k'):
    """
    Takes a 2d array and colormap name, scales the input, and returns a RGB uint8 array
    """
    scaled = (arr - np.nanmin(arr)) / (np.nanmax(arr) - np.nanmin(arr))
    scaled = scaled * (vmax - vmin) + vmin
    cmap = get_cmap(cmap)
    rgb = cmap(scaled, bytes=True)[:, :, :3]
    rgb[np.isnan(scaled)] = np.array(to_rgb(nan_color), dtype='uint8') * 255
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
    mtr_caxis = 180 / np.pi * np.arccos(dotproduct / (magA * magB))  # %misalignment of every feature relative to stress axis
    mtr_caxis[mtr_caxis > 90] = 180 - mtr_caxis[mtr_caxis > 90]

    return mtr_caxis


def getRegionProp(grainID_map, prop='solidity'):
    props = []
    label = []
    for region in regionprops(grainID_map):
        label.append(region.label)
        props.append(region[prop])
    df = DataFrame(label, columns=['Label'])
    df[prop] = props
    df = df.set_index('Label')
    return df


def read_dream3d_file(d3d, ref_dir=[0, 0, 1], mtr_size=10000):
    data = h5py.File(d3d, 'r')
    d = {}
    d['fname'] = os.path.basename(d3d).split(".dream3d")[0]
    d['eulers'] = data['DataContainers/ImageDataContainer/CellFeatureData/AvgEuler'][1:]
    d['phases'] = data['DataContainers/ImageDataContainer/CellFeatureData/Phases'][1:]
    d['num_neighbors'] = data['DataContainers/ImageDataContainer/CellFeatureData/NumNeighbors2'][1:]
    d['sizes'] = data['DataContainers/ImageDataContainer/CellFeatureData/EquivalentDiameters'][1:]
    try:
        d['neighbor_list'] = data['DataContainers/ImageDataContainer/CellFeatureData/NeighborList2'][:].tolist()
        d['shared_surfaces'] = data['DataContainers/ImageDataContainer/CellFeatureData/SharedSurfaceAreaList2'][:].tolist()
    except:
        pass
    d['avg_caxis'] = data['DataContainers/ImageDataContainer/CellFeatureData/AvgCAxes'][1:]
    d['mask'] = data['DataContainers/ImageDataContainer/CellData/Mask'][0, :, :, 0]

    try:
        d['raw_caxis'] = data['DataContainers/ImageDataContainer/CellData/Raw_CAxes'][0]
        d['caxis_misalignments'] = calc_misalignment(d['raw_caxis'].reshape(-1, 3), ref_dir=ref_dir).reshape(
            d['raw_caxis'].shape[:2]
        )

    except:
        pass

    d['cells'] = data['/DataContainers/ImageDataContainer/CellFeatureData/NumCells'][1:].ravel()

    d['volumes'] = data['DataContainers/ImageDataContainer/CellFeatureData/Volumes'][1:].ravel()
    d['centroids'] = data['DataContainers/ImageDataContainer/CellFeatureData/Centroids'][1:]
    d['misorientation'] = data['DataContainers/ImageDataContainer/CellFeatureData/FeatureAvgCAxisMisorientations'][1:].ravel()
    d['grainIDs'] = data['/DataContainers/ImageDataContainer/CellData/MTRIds'][0, :, :, 0]

    # IPF Z Direction
    d['ipf_raw_z'] = data['DataContainers/ImageDataContainer/CellData/IPF_Raw_Z'][0]  # shape (1, 1000, 1001, 3)
    d['ipf_cleaned_z'] = data['DataContainers/ImageDataContainer/CellData/IPF_Cleaned_Z'][0]  # shape (1, 1000, 1001, 3)
    d['ipf_avg_z'] = data['DataContainers/ImageDataContainer/CellData/IPF_Average_Z'][0]  # shape (1, 1000, 1001, 3)
    d['ipf_mtr_z'] = data['DataContainers/ImageDataContainer/CellData/IPF_MTR_Z'][0]  # shape (1, 1000, 1001, 3)

    # IPF Y Direction
    d['ipf_raw_y'] = data['DataContainers/ImageDataContainer/CellData/IPF_Raw_Y'][0]  # shape (1, 1000, 1001, 3)
    d['ipf_cleaned_y'] = data['DataContainers/ImageDataContainer/CellData/IPF_Cleaned_Y'][0]  # shape (1, 1000, 1001, 3)
    d['ipf_avg_y'] = data['DataContainers/ImageDataContainer/CellData/IPF_Average_Y'][0]  # shape (1, 1000, 1001, 3)
    d['ipf_mtr_y'] = data['DataContainers/ImageDataContainer/CellData/IPF_MTR_Y'][0]  # shape (1, 1000, 1001, 3)

    # IPF X Direction
    d['ipf_raw_x'] = data['DataContainers/ImageDataContainer/CellData/IPF_Raw_X'][0]  # shape (1, 1000, 1001, 3)
    d['ipf_cleaned_x'] = data['DataContainers/ImageDataContainer/CellData/IPF_Cleaned_X'][0]  # shape (1, 1000, 1001, 3)
    d['ipf_avg_x'] = data['DataContainers/ImageDataContainer/CellData/IPF_Average_X'][0]  # shape (1, 1000, 1001, 3)
    d['ipf_mtr_x'] = data['DataContainers/ImageDataContainer/CellData/IPF_MTR_X'][0]  # shape (1, 1000, 1001, 3)

    d['raw_eulers'] = data['DataContainers/ImageDataContainer/CellData/EulerAngles'][0]  # shape (1, 1000, 1001, 3)
    d['avg_eulers'] = data['DataContainers/ImageDataContainer/CellData/AvgEulerAngles'][0]  # shape (1, 1000, 1001, 3)
    d['twist_angles'] = np.abs(d['eulers'][:, -1] * 180 / np.pi) % 30

    ind = np.where(d['volumes'] >= mtr_size)[0]
    d['Number_MTRS'] = len(ind)
    d['mtr_sizes'] = d['volumes'][ind]
    d['mtr_circle_diameters_um'] = np.sqrt(4 * d['mtr_sizes'] / np.pi)  # A = pi*r**2  --> D = sqrt(4*A/pi)

    d['mtr_misorientations'] = d['misorientation'][ind]
    d['mtr_caxis_misalignments'] = calc_misalignment(d['avg_caxis'][ind].reshape(-1, 3), ref_dir=ref_dir)

    bins = [0, 25, 40, 60, 70, 100]
    labels = ['Hard', 'Misc', 'Initiator', 'Misc', 'Soft']
    df = DataFrame({'misalignment': d['mtr_caxis_misalignments']})
    mtr_class = cut(df['misalignment'], bins, labels=False).map({i: x for i, x in enumerate(labels)}).values.tolist()
    d['mtr_class'] = mtr_class

    mtr_ind = ind + 1
    mtr_mask = isin(d['grainIDs'], mtr_ind)
    mtr_ids = d['grainIDs'].copy()
    mtr_ids[~mtr_mask] = 0
    d['mtr_mask'] = mtr_mask
    d['mtr_id_map'] = mtr_ids

    minor_axis_length = getRegionProp(mtr_ids, prop='minor_axis_length')
    major_axis_length = getRegionProp(mtr_ids, prop='major_axis_length')
    mtr_aspect_ratios = major_axis_length['major_axis_length'] / minor_axis_length['minor_axis_length']
    d['mtr_aspect_ratios'] = mtr_aspect_ratios

    solidity = getRegionProp(mtr_ids, prop='solidity')
    solidity = solidity['solidity'].values
    d['mtr_solidity'] = solidity
    d['mtr_intensity'] = (
        d['mtr_sizes'] * solidity * np.cos(d['mtr_caxis_misalignments'] * np.pi / 180) / d['mtr_misorientations'] / 1e4
    )

    mtr_ipf = d['ipf_cleaned_z'].copy()
    mtr_ipf[~mtr_mask] = 0
    d['mtr_ipf'] = mtr_ipf
    d['stepsize'] = np.sqrt(np.mean(d['volumes'] / d['cells']))

    ind = np.sum(d['ipf_cleaned_z'], axis=2) > 0
    scan_area_pct = np.sum(ind.astype('uint8')) / (float(ind.shape[0]) * ind.shape[1])
    dim1, dim2 = d['ipf_cleaned_z'].shape[0] * d['stepsize'] / 1000.0, d['ipf_cleaned_z'].shape[1] * d['stepsize'] / 1000.0
    area = scan_area_pct * dim1 * dim2
    d['scan_area_mm2'] = area

    # Calculate fraction alterred
    elemwise_check = d['ipf_cleaned_z'] == d['ipf_raw_z']
    elemwise_delta = np.all(elemwise_check, axis=-1)
    d['pixel_fraction_altered_by_cleanup'] = (elemwise_delta.size - elemwise_delta.sum()) / elemwise_delta.size

    return d


def create_cpm_cmap(d3d, reference_frame='HKL', reference_direction='001'):
    caxis = np.abs(d3d['raw_caxis'])
    cmap = np.empty_like(caxis).astype('uint8')

    if reference_frame == 'TSL':
        if reference_direction == '001':
            cmap[:, :, 0] = (caxis[:, :, 2] * 255).astype('uint8')  # R
            cmap[:, :, 1] = (caxis[:, :, 0] * 255).astype('uint8')  # G
            cmap[:, :, 2] = (caxis[:, :, 1] * 255).astype('uint8')  # B
        elif reference_direction == '010':
            cmap[:, :, 0] = (caxis[:, :, 1] * 255).astype('uint8')  # B
            cmap[:, :, 1] = (caxis[:, :, 2] * 255).astype('uint8')  # R
            cmap[:, :, 2] = (caxis[:, :, 0] * 255).astype('uint8')  # G
        elif reference_direction == '100':
            cmap[:, :, 0] = (caxis[:, :, 0] * 255).astype('uint8')  # B
            cmap[:, :, 1] = (caxis[:, :, 1] * 255).astype('uint8')  # R
            cmap[:, :, 2] = (caxis[:, :, 2] * 255).astype('uint8')  # G

    elif reference_frame == 'HKL':
        if reference_direction == '001':
            cmap[:, :, 0] = (caxis[:, :, 2] * 255).astype('uint8')  # R
            cmap[:, :, 1] = (caxis[:, :, 0] * 255).astype('uint8')  # G
            cmap[:, :, 2] = (caxis[:, :, 1] * 255).astype('uint8')  # B
        elif reference_direction == '100':
            cmap[:, :, 0] = (caxis[:, :, 1] * 255).astype('uint8')  # B
            cmap[:, :, 1] = (caxis[:, :, 2] * 255).astype('uint8')  # R
            cmap[:, :, 2] = (caxis[:, :, 0] * 255).astype('uint8')  # G
        elif reference_direction == '010':
            cmap[:, :, 0] = (caxis[:, :, 0] * 255).astype('uint8')  # B
            cmap[:, :, 1] = (caxis[:, :, 1] * 255).astype('uint8')  # R
            cmap[:, :, 2] = (caxis[:, :, 2] * 255).astype('uint8')  # G

    cmap[~d3d['mask'].astype('bool')] = [0, 0, 0]
    return cmap


def isin(element, test_elements, assume_unique=False, invert=False):
    "..."
    element = np.asarray(element)
    return np.in1d(element, test_elements, assume_unique=assume_unique, invert=invert).reshape(element.shape)


def add_scalebar(d3d=None, length_pct=0.25, plot=False, rgb_image=None, stepsize=None):
    """
    If a d3d data dictionary is provided, the script will read the IPF image and add a scalebar automatically based on stepsize
    Otherwise, if an rgb_image and stepsize (um_per_px) are provided and d3d=None, then it will use the manually provided inputs
    """

    # Crop off bottom to remove scalebar
    if sys.platform == 'linux':
        font_name = "DejaVuSans"
    else:
        font_name = "arial"
    # colors = ["black"]
    units = ['mm']

    if isinstance(d3d, dict):
        rgb_image = fromarray(d3d['ipf_cleaned_z'].copy())
        stepsize = d3d['stepsize']  # um_per_px

    elif isinstance(rgb_image, np.ndarray) and np.isreal(stepsize):
        rgb_image = fromarray(rgb_image).copy()

    w, h = rgb_image.size

    # assign font, size, color
    fontsize = np.floor(0.03 * h).astype('int32')
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

    text_str = '%.3f %s' % (length * stepsize / 1000, units[0])

    # Draw Text and Scalebar
    draw = Draw(rgb_image)
    text_length = draw.textlength(text=text_str, font=font)
    # larger_feature_length = max([text_length, length])
    x_text_center = int(xs + 0.5 * text_length)
    line_center = int(xs + 0.5 * length)
    x_text_offset = line_center - x_text_center

    # Draw Background
    draw.rectangle(xy=xy_bg, fill=(255, 255, 255))
    draw.text(xy=(xs + x_text_offset, ys + 1 * offset), text=text_str, font=font, fill=(0, 0, 0), align='center')
    draw.line(xy=xy, width=thickness, fill=(0, 0, 0))

    image_w_scalebar = np.array(rgb_image)

    # if plot:
    #     plt.imshow(image_w_scalebar); plt.pause(.1)

    return image_w_scalebar


def setup_directories(parent_dir, subdirectories):
    for folder in subdirectories:
        try:
            os.makedirs(os.path.join(parent_dir, folder, 'IPF_Images', 'X'))
            os.makedirs(os.path.join(parent_dir, folder, 'IPF_Images', 'Y'))
            os.makedirs(os.path.join(parent_dir, folder, 'IPF_Images', 'Z'))
        except:
            continue


def create_d3d_input_files_v65_ang(input_dictionary):
    """
    inputs_dictionary = dict(output_folder_name = string, caxis_misalignment = string), comparison_value = string, hkl_ipf_dir = [], file_paths = [])
    """
    # template_path = '../Templates/PW_standard_routine_v65.json'
    template_path = Config().dream3d_pipeline_template('ang')

    with open(template_path, 'r') as f:
        template = json.load(f)

    for key in input_dictionary['paths'].keys():
        template['00']['InputFile'] = input_dictionary['paths'][key]['input_path']
        template['08']['SelectedThresholds'][0]['Comparison Value'] = float(input_dictionary['mask1_value'])
        template['08']['SelectedThresholds'][1]['Comparison Value'] = float(input_dictionary['mask2_value'])
        template['13']['MinConfidence'] = float(input_dictionary['primary_cleanup_value'])
        template['14']['MinConfidence'] = float(input_dictionary['secondary_cleanup_value'])
        template['16']['MisorientationTolerance'] = int(input_dictionary['caxis_misalignment'])

        template['09']['OutputPath'] = input_dictionary['paths'][key]['initial_pole_figure']
        template['44']['OutputPath'] = input_dictionary['paths'][key]['final_pole_figure']
        template['45']['OutputPath'] = input_dictionary['paths'][key]['mtr_pole_figure']

        template['40']['SelectedThresholds'][0]['Comparison Value'] = float(input_dictionary['min_mtr_size'])

        template['46']['FileName'] = input_dictionary['paths'][key]['raw_ipf_z']
        template['47']['FileName'] = input_dictionary['paths'][key]['cleaned_ipf_z']
        template['48']['FileName'] = input_dictionary['paths'][key]['average_ipf_z']
        template['49']['FileName'] = input_dictionary['paths'][key]['mtr_ipf_z']

        template['50']['OutputFile'] = input_dictionary['paths'][key]['dream3d']

        with open(input_dictionary['paths'][key]['json_path'], 'w') as f:
            json.dump(template, f, indent=4)


def create_d3d_input_files_v65_ctf(input_dictionary):
    """
    inputs_dictionary = dict(output_folder_name = string, caxis_misalignment = string), comparison_value = string, hkl_ipf_dir = [], file_paths = [])
    """
    template_path = Config().dream3d_pipeline_template('ctf')

    with open(template_path, 'r') as f:
        template = json.load(f)

    for key in input_dictionary['paths'].keys():
        template['00']['InputFile'] = input_dictionary['paths'][key]['input_path']
        template['10']['SelectedThresholds'][0]['Comparison Value'] = float(input_dictionary['mask1_value'])
        template['15']['MinConfidence'] = float(input_dictionary['primary_cleanup_value'])
        template['16']['MinConfidence'] = float(input_dictionary['secondary_cleanup_value'])

        template['18']['MisorientationTolerance'] = int(input_dictionary['caxis_misalignment'])

        template['11']['OutputPath'] = input_dictionary['paths'][key]['initial_pole_figure']
        template['46']['OutputPath'] = input_dictionary['paths'][key]['final_pole_figure']
        template['47']['OutputPath'] = input_dictionary['paths'][key]['mtr_pole_figure']

        template['42']['SelectedThresholds'][0]['Comparison Value'] = float(input_dictionary['min_mtr_size'])

        template['48']['FileName'] = input_dictionary['paths'][key]['raw_ipf_z']
        template['49']['FileName'] = input_dictionary['paths'][key]['cleaned_ipf_z']
        template['50']['FileName'] = input_dictionary['paths'][key]['average_ipf_z']
        template['51']['FileName'] = input_dictionary['paths'][key]['mtr_ipf_z']

        template['52']['OutputFile'] = input_dictionary['paths'][key]['dream3d']

        with open(input_dictionary['paths'][key]['json_path'], 'w') as f:
            json.dump(template, f, indent=4)


def runner(list_of_input_files):
    d3d_path = Config().dream3d_pipeline_runner
    if not list_of_input_files:
        fids = glob.glob(os.path.join('./', "*", "*.json"))
    for fid in fids:
        command = d3d_path + ' -p ' + fid
        os.system(command)
