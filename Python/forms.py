from tkinter import Text, TOP, BOTH, X, LEFT, RIGHT, StringVar, END, NW, WORD
from tkinter.ttk import Frame, Label, Entry, Button, Style, Progressbar, Radiobutton
from functools import partial
from tkinter import filedialog, messagebox, IntVar
from types import SimpleNamespace
import os
import json
import glob
import yaml
import time
import re
import numpy as np
import subprocess
import psutil
from utils import setup_directories, create_d3d_input_files_v65_ang, create_d3d_input_files_v65_ctf
from utils import read_dream3d_file, add_scalebar, array2rgb
from skimage.segmentation import mark_boundaries
from pandas import DataFrame, concat, ExcelWriter
import warnings
from imageio import imsave

_FONTS = SimpleNamespace(
    label=("DejaVu Sans", 14, "bold"),
    small=("DejaVu Sans", 14),
)


# Good habit to put your GUI in a class to make it self-contained
class Dream3dMicrotextureAnalysis(Frame):

    def __init__(self):
        super().__init__()
        # self allow the variable to be used anywhere in the class
        self.file_paths = []
        self.lw = 30
        self.initUI()

    def initUI(self):

        # self.master.title("Microtexture Analysis Setup")
        self.pack(fill=BOTH, expand=True)

        # ========================================================================================================================
        frame0 = Frame(self)
        frame0.pack(fill=X)
        # Command tells the form what to do when the button is clicked
        btn0 = Button(frame0, text="Select Results Directory", command=self.onLoad)
        btn0.pack(in_=frame0, padx=5, pady=10, side=LEFT)
        # ========================================================================================================================

        self.text = StringVar()
        self.text.set("Dream3D Files Found: 0")
        label0a = Label(self, textvariable=self.text)
        label0a.pack(in_=frame0, padx=5, pady=10, side=LEFT)
        # ========================================================================================================================

        frame2 = Frame(self)
        frame2.pack(fill=X)
        lbl2 = Label(
            frame2,
            text="Minimum MTR Size, um^2:",
            width=self.lw,
            anchor='e',
            justify=RIGHT,
            font=_FONTS.label,
            background='#f2f2f2',
        )
        lbl2.pack(side=LEFT, padx=5, pady=10)
        self.entry2 = Entry(frame2)
        self.entry2.pack(fill=X, padx=5, expand=True)
        self.entry2.insert(-1, '10000')
        # ========================================================================================================================

        frame4 = Frame(self)
        frame4.pack(fill=X)
        lbl4 = Label(
            frame4,
            text="Stress Axis Direction:",
            width=self.lw,
            anchor='e',
            justify=RIGHT,
            font=_FONTS.label,
            background='#f2f2f2',
        )
        lbl4.pack(side=LEFT, padx=5, pady=10)
        self.entry4 = Entry(frame4)
        self.entry4.pack(fill=X, padx=5, expand=True)
        self.entry4.insert(-1, '[0,0,1]')
        # ========================================================================================================================

        frame6 = Frame(self)
        frame6.pack(fill=X)
        self.progresstext = StringVar()
        self.progresstext.set("Progress: n/a")
        lbl6 = Label(self, textvariable=self.progresstext)
        lbl6.pack()
        # ========================================================================================================================

        progressbar = Progressbar(self, orient='horizontal', mode='determinate', length=400)
        progressbar.pack()  # expand=True, padx=20)
        self.pb = progressbar

        frame7 = Frame(self)
        frame7.pack(fill=X)
        btn1 = Button(frame7, text='Submit Analysis', command=self.onSubmit)
        btn1.pack(in_=frame7, padx=5, pady=5)
        # ========================================================================================================================

        frame8 = Frame(self)
        frame8.pack(fill=X)

        self.note = StringVar()
        self.note.set(
            "* The GUI may appear to freeze during this analysis, but it's usually still working in the background. Please be patient."
        )
        label1 = Label(self, textvariable=self.note)
        label1.pack(in_=frame8, padx=5, pady=20, side=LEFT)
        # ========================================================================================================================

    def set_progressbar_value(self, value):
        self.pb['value'] = value
        self.progresstext.set("Current Progress: %d" % value + '% complete')
        self.update_idletasks()

    def onLoad(self):
        options = dict(title='Select Parent Results Directory', mustexist=True)
        parent_dir = filedialog.askdirectory(**options)
        if len(parent_dir):
            self.file_paths = glob.glob(os.path.join(parent_dir, '*', '*.dream3d'))
        self.parent_dir = parent_dir
        self.text.set('Dream3D Files Found: %d' % len(self.file_paths))

    def onSubmit(self):

        if len(self.file_paths) > 0:
            # do something
            self.min_mtr_size = int(self.entry2.get())
            self.stress_axis_direction = self.entry4.get()
            self.analyzeData()
        else:
            response = messagebox.showwarning(
                title='Warning',
                message="No Dream3D file(s) were located. Verify path directory. Are you sure you want to exit?",
                type='yesno',
            )
            if response == 'yes':
                self.quit()

    def analyzeData(self):

        warnings.simplefilter(action='ignore', category=RuntimeWarning)
        # Write Input Files
        if len(self.file_paths):

            str_stress_axis_direction = ''.join(list(map(str, re.findall('\d', self.stress_axis_direction))))  # string format
            int_stress_axis_direction = list(map(int, str_stress_axis_direction))  # self. format

            min_mtr_size = self.min_mtr_size
            d3d_paths = self.file_paths

            raw_data = DataFrame()
            scan_areas = {}
            pct_altered = {}

            # Do something
            self.progresstext.set('Loading File...')
            self.update_idletasks()

            for n, fid in enumerate(d3d_paths):
                if os.path.exists(fid):
                    d3d = read_dream3d_file(fid, ref_dir=int_stress_axis_direction, mtr_size=min_mtr_size)

                    # Load Raw Data and Add to Single Dataframe
                    data = np.c_[
                        d3d['mtr_sizes'],
                        d3d['mtr_misorientations'],
                        d3d['mtr_caxis_misalignments'],
                        d3d['mtr_solidity'],
                        d3d['mtr_intensity'],
                        d3d['mtr_aspect_ratios'],
                    ]
                    new_raw_data = DataFrame(
                        data,
                        columns=[
                            'MTR Area, um^2',
                            'MTR Misorientation, deg',
                            'MTR Caxis Misalignment, deg',
                            'Solidity',
                            'MTR Intensity',
                            'MTR Aspect Ratio',
                        ],
                    )
                    new_raw_data['Sample'] = d3d['fname']
                    new_raw_data['MTR Class'] = d3d['mtr_class']
                    raw_data = concat([raw_data, new_raw_data], axis=0)

                    # Generate and Save IPF Image with Scalebar

                    # Generate MTR ID Map and Save
                    mtr_id_map = array2rgb(d3d['mtr_id_map'], cmap='nipy_spectral')
                    mtr_id_map_w_boundaries = (
                        mark_boundaries(mtr_id_map, d3d['mtr_id_map'], color=(1, 1, 1), mode='inner') * 255
                    ).astype('uint8')
                    mtr_id_map_with_scalebar = add_scalebar(
                        d3d=None, rgb_image=mtr_id_map_w_boundaries, stepsize=d3d['stepsize'], plot=False
                    )
                    imsave(os.path.join(os.path.dirname(fid), 'Individual_MTRs.png'), np.array(mtr_id_map_with_scalebar))

                    for ref in ['x', 'y', 'z']:
                        ipf_with_scalebar = add_scalebar(
                            d3d=None, rgb_image=d3d[f'ipf_cleaned_{ref.lower()}'], stepsize=d3d['stepsize'], plot=False
                        )
                        imsave(
                            os.path.join(
                                os.path.dirname(fid), 'IPF_Images', ref.upper(), f'IPF_Cleaned_{ref.upper()}_Image_w_Scalebar.png'
                            ),
                            ipf_with_scalebar,
                        )

                        # Generate MTR Only IPF Map and Save
                        mtr_ipf_with_scalebar = add_scalebar(
                            d3d=None, rgb_image=d3d[f'ipf_mtr_{ref.lower()}'], stepsize=d3d['stepsize'], plot=False
                        )
                        imsave(
                            os.path.join(
                                os.path.dirname(fid), 'IPF_Images', ref.upper(), f'IPF_MTR_{ref.upper()}_Image_w_Scalebar.png'
                            ),
                            mtr_ipf_with_scalebar,
                        )

                    scan_areas[d3d['fname']] = d3d['scan_area_mm2']
                    pct_altered[d3d['fname']] = d3d['pixel_fraction_altered_by_cleanup']

                    progress = int((n + 1) / len(d3d_paths) * 100)
                    self.set_progressbar_value(progress)
                    self.update()
                    self.update_idletasks()

            if len(raw_data):
                # Get Groups by Scan and MTR Class
                raw_data.replace([np.inf, -np.inf], np.nan, inplace=True)
                raw_data.dropna(inplace=True)

                grps = raw_data.groupby(['Sample', 'MTR Class'])

                # Calculate Descriptive Statistics
                stats = grps.describe()

                # Calculate Area Fraction
                stats2 = grps.agg(Total_Area_um2=('MTR Area, um^2', sum)).reset_index()
                stats2['Area Fraction'] = stats2.apply(lambda x: x['Total_Area_um2'] / 1000**2 / scan_areas[x['Sample']], axis=1)

                # Calculate Number Density
                counts = grps.agg(Count=('MTR Area, um^2', len)).reset_index()
                stats2['Count'] = counts['Count']
                stats2['Number Density (Qty/mm)'] = counts.apply(lambda x: x['Count'] / scan_areas[x['Sample']], axis=1)

                scan_areas = DataFrame.from_dict(scan_areas, orient='index', columns=['Scan Area, mm2'])
                pct_altered = DataFrame.from_dict(pct_altered, orient='index', columns=['Pixel Fraction Altered By Cleanup'])

                scan_areas = scan_areas.join(pct_altered)

                # Save Summary Statistics to Results Folder
                output_path = os.path.join(self.parent_dir, 'Microtexture Statistics Summary.xlsx')

                writer = ExcelWriter(output_path)

                # Unroll Multi-index columns and write each dataset to its own tab
                columns = np.unique([n[0] for n in stats.columns])

                for col in columns:
                    stats = stats.rename(columns={'count': 'number_of_mtrs'})
                    stats[col].to_excel(writer, sheet_name=col, float_format='%.4f')

                stats2.to_excel(writer, sheet_name='Area Fractions', float_format='%.4f')
                scan_areas.to_excel(writer, sheet_name='Scan Areas and Cleanup Summary', float_format='%.4f')
                writer.close()

                raw_data_output_path = os.path.join(self.parent_dir, 'Raw Data.csv')
                raw_data = raw_data[
                    [
                        'Sample',
                        'MTR Class',
                        'MTR Area, um^2',
                        'MTR Caxis Misalignment, deg',
                        'MTR Misorientation, deg',
                        'Solidity',
                        'MTR Intensity',
                        'MTR Aspect Ratio',
                    ]
                ]
                raw_data.to_csv(raw_data_output_path)

            else:
                response = messagebox.showwarning(
                    title='Warning',
                    message="No MTRs identified using current settings. Hit 'Yes' to Exit. Hit 'No' remain and adjust settings.",
                    type='yesno',
                )
                if response == 'yes':
                    self.quit()

            response = messagebox.showinfo(
                title='Microtexture Analysis Status',
                message="Program has completed successfully. Click 'Yes' to Exit or 'No' to remain.",
                type='yesno',
            )
            if response == 'yes':
                self.quit()
            self.set_progressbar_value(0.0)
            self.progresstext.set('Analysis complete.')


class GenericPipelineBuilderUI(Frame):
    def __init__(self, gui_mode=True):
        super().__init__()
        self.gui_mode = gui_mode
        self.lw = 30
        self.initUI()

    def initUI(self):

        self.pack(fill=BOTH, expand=True)
        # ========================================================================================================================
        frame0 = Frame(self)
        frame0.pack(fill=X)
        # Command tells the form what to do when the button is clicked
        btn0 = Button(frame0, text="Select .ANG or .CTF Files", command=self.onLoadFiles)
        btn0.pack(in_=frame0, padx=5, pady=10, side=LEFT)

        self.text = StringVar()
        self.text.set("Selected Files: 0")
        label0a = Label(self, textvariable=self.text)
        label0a.pack(in_=frame0, padx=5, pady=10, side=LEFT)
        # ========================================================================================================================

        frame1 = Frame(self)
        frame1.pack(fill=X)
        lbl1 = Label(
            frame1,
            text="Output Folder Name:",
            width=self.lw,
            anchor='e',
            justify=RIGHT,
            font=_FONTS.label,
            background='#f2f2f2',
        )
        lbl1.pack(side=LEFT, padx=5, pady=10)
        self.entry1 = Entry(frame1, width=10)
        self.entry1.pack(fill=X, padx=10, expand=True)
        self.entry1.insert(-1, 'Results')
        # ========================================================================================================================

        frame2 = Frame(self)
        frame2.pack(fill=X)
        lbl2 = Label(
            frame2,
            text="C-Axis Misalignment Threshold (deg)\n For Pixel Segmentation: ",
            width=self.lw,
            anchor='e',
            justify=RIGHT,
            font=_FONTS.label,
            background='#f2f2f2',
        )
        lbl2.pack(side=LEFT, padx=5, pady=10)
        self.entry2 = Entry(frame2)
        self.entry2.pack(fill=X, padx=10, expand=True)
        self.entry2.insert(-1, '20')
        # ========================================================================================================================

        s = Style()
        s.configure('cleanup.TFrame', background='#f2f2f2')

        frame3a = Frame(self)
        frame3a.pack(fill=X)

        self.mask_text = StringVar()
        self.mask_text.set("*Threshold for Good Data:")
        lbl3_mask1_main = Label(
            frame3a,
            textvariable=self.mask_text,
            width=self.lw,
            anchor='e',
            justify=RIGHT,
            font=_FONTS.label,
            background='#f2f2f2',
        )
        lbl3_mask1_main.pack(side=LEFT, padx=5, pady=5)
        # ========================================================================================================================

        frame3b = Frame(self)
        frame3b.pack(fill=X)

        self.mask1_text = StringVar()
        self.mask1_text.set("CI > ")
        lbl3_mask1 = Label(frame3b, textvariable=self.mask1_text, width=self.lw, anchor='e', font=_FONTS.small, justify=RIGHT)
        lbl3_mask1.pack(side=LEFT, padx=5, pady=0)
        self.mask1_value = Entry(frame3b)
        self.mask1_value.pack(fill=X, padx=10, expand=True)
        self.mask1_value.insert(-1, '0.05')
        # ========================================================================================================================

        frame3c = Frame(self)
        frame3c.pack(fill=X)

        self.mask2_text = StringVar()
        self.mask2_text.set("IQ > ")
        lbl3_mask2 = Label(frame3c, textvariable=self.mask2_text, width=self.lw, anchor='e', justify=RIGHT, font=_FONTS.small)
        lbl3_mask2.pack(side=LEFT, padx=5, pady=0)
        self.mask2_value = Entry(frame3c)
        self.mask2_value.pack(fill=X, padx=10, expand=True)
        self.mask2_value.insert(-1, '20000')
        # ========================================================================================================================

        frame4 = Frame(self)
        frame4.pack(fill=X)

        self.cleanup1_text = StringVar()
        self.cleanup1_text.set("*Threshold for Primary Cleanup:")
        lbl_primary_cleanup = Label(
            frame4,
            textvariable=self.cleanup1_text,
            width=self.lw,
            anchor='e',
            font=_FONTS.label,
            justify=RIGHT,
            background='#f2f2f2',
        )
        lbl_primary_cleanup.pack(side=LEFT, padx=5, pady=5)
        # ========================================================================================================================

        frame4a = Frame(self)
        frame4a.pack(fill=X)
        self.primary_cleanup_text = StringVar()
        self.primary_cleanup_text.set("CI < ")
        lbl_primary_cleanup_value = Label(
            frame4a, textvariable=self.primary_cleanup_text, width=self.lw, anchor='e', justify=RIGHT, font=_FONTS.small
        )
        lbl_primary_cleanup_value.pack(side=LEFT, padx=5, pady=0)
        self.primary_cleanup_value = Entry(frame4a)
        self.primary_cleanup_value.pack(fill=X, padx=10, expand=True)
        self.primary_cleanup_value.insert(-1, '0.05')
        # ========================================================================================================================

        frame4b = Frame(self)
        frame4b.pack(fill=X)

        self.secondary_cleanup_header_text = StringVar()
        self.secondary_cleanup_header_text.set("*Threshold for Secondary Cleanup:")
        lbl_secondary_cleanup = Label(
            frame4b,
            textvariable=self.secondary_cleanup_header_text,
            width=self.lw,
            anchor='e',
            font=_FONTS.label,
            justify=RIGHT,
            background='#f2f2f2',
        )
        lbl_secondary_cleanup.pack(side=LEFT, padx=0, pady=5)
        # ========================================================================================================================

        frame4c = Frame(self)
        frame4c.pack(fill=X)

        self.secondary_cleanup_text = StringVar()
        self.secondary_cleanup_text.set("CI < ")
        lbl_secondary_cleanup_value = Label(
            frame4c, textvariable=self.secondary_cleanup_text, width=self.lw, anchor='e', font=_FONTS.small
        )
        lbl_secondary_cleanup_value.pack(side=LEFT, padx=5, pady=0)
        self.secondary_cleanup_value = Entry(frame4c)
        self.secondary_cleanup_value.pack(fill=X, padx=10, expand=True)
        self.secondary_cleanup_value.insert(-1, '0.10')
        # ========================================================================================================================

        frame5 = Frame(self)
        frame5.pack(fill=X)
        lbl_mtr_size = Label(
            frame5,
            text="Minimum MTR Size, um^2:",
            width=self.lw,
            anchor='e',
            justify=RIGHT,
            font=_FONTS.label,
            background='#f2f2f2',
        )
        lbl_mtr_size.pack(side=LEFT, padx=5, pady=10)
        self.entry4 = Entry(frame5)
        self.entry4.pack(fill=X, padx=10, expand=True)
        self.entry4.insert(-1, '10000')
        # ========================================================================================================================

        frame6 = Frame(self)
        frame6.pack(fill=X)
        lbl_version = Label(
            frame6,
            text="Dream3D Version:",
            width=self.lw,
            anchor='e',
            justify=RIGHT,
            font=_FONTS.label,
            background='#f2f2f2',
        )
        lbl_version.pack(side=LEFT, padx=5, pady=10)

        self.int_dream3d_version = IntVar()
        self.rbtn2 = Radiobutton(
            frame6,
            text="DREAM3D-6.5.49-Win64",
            variable=self.int_dream3d_version,
            value=0,
            command=partial(self.getDream3DVersionAndFileExtension, True),
        )
        self.rbtn2.pack(fill=X, padx=10, expand=True)
        # ========================================================================================================================

        frame7 = Frame(self)
        frame7.pack(fill=X, pady=10)
        lbl7 = Label(
            frame7,
            text="Overwrite Existing Files?",
            width=self.lw,
            anchor='e',
            justify=RIGHT,
            font=_FONTS.label,
            background='#f2f2f2',
        )
        lbl7.pack(side=LEFT, padx=5, pady=10)

        self.int_overwrite = IntVar()
        self.rbtn3 = Radiobutton(frame7, text="No", variable=self.int_overwrite, value=0)
        self.rbtn3.pack(fill=X, padx=10, expand=True)
        self.rbtn4 = Radiobutton(frame7, text="Yes", variable=self.int_overwrite, value=1)
        self.rbtn4.pack(fill=X, padx=10, expand=True)
        # ========================================================================================================================

        frame8 = Frame(self)
        frame8.pack(fill=X)
        self.choice_text = StringVar()
        self.choice_text.set("Select A Run Option Below")
        label8 = Label(self, textvariable=self.choice_text)
        label8.pack(in_=frame8, pady=5)
        # ========================================================================================================================

        frame9 = Frame(self)
        frame9.pack(pady=10)  # side=BOTTOM, pady=10)
        btn5 = Button(frame9, text='Generate Input File(s)', command=partial(self.onGenerateFiles))
        btn5.pack(in_=frame9, side=LEFT, padx=5)

        btn6 = Button(frame9, text='Load Existing Input File(s)', command=partial(self.onLoadDirectory))
        btn6.pack(in_=frame9, side=LEFT, padx=5)

        btn7 = Button(frame9, text='Submit to Dream3D', command=partial(self.onSubmit))
        btn7.pack(in_=frame9, side=LEFT, padx=5)
        # ========================================================================================================================

        frame10 = Frame(self)
        frame10.pack(fill=X)

        self.note = StringVar()
        self.note.set(
            "* It is recommended that end users perform a study to establish appropriate threshold values for data cleaning."
        )
        label10 = Label(self, textvariable=self.note)
        label10.pack(in_=frame10, padx=5, pady=20, side=LEFT)
        # ========================================================================================================================

        if not self.gui_mode:
            self.master.destroy()

    def onLoadFiles(self, all_file_paths=None):
        self.file_paths = []

        options = dict(title='Select .ANG or .CTF Files', initialdir='../', filetypes=[('.ANG', '*.ang'), ('.CTF', '*.ctf')])
        if all_file_paths is not None:
            self.all_file_paths = all_file_paths
        else:
            self.all_file_paths = filedialog.askopenfilenames(**options)

        self.file_paths = self.verifyFilePaths(self.all_file_paths)

        if len(self.file_paths):

            extensions = [re.findall(r'\.\w{3}$', n)[0] for n in self.file_paths]

            if len(self.file_paths):
                if self.gui_mode:
                    if '.ctf' in extensions:
                        self.mask1_text.set("Error < ")
                        self.mask1_value.delete(0, END)
                        self.mask1_value.insert(0, '1')

                        self.mask2_text.set("N/A")
                        self.mask2_value.delete(0, END)
                        self.mask2_value.insert(0, '')

                        self.primary_cleanup_text.set("BC < ")
                        self.primary_cleanup_value.delete(0, END)
                        self.primary_cleanup_value.insert(0, '30')

                        self.secondary_cleanup_text.set("BC < ")
                        self.secondary_cleanup_value.delete(0, END)
                        self.secondary_cleanup_value.insert(0, '50')

                    elif '.ang' in extensions:
                        self.mask1_text.set("CI > ")
                        self.mask1_value.delete(0, END)
                        self.mask1_value.insert(0, '0.05')

                        self.mask2_text.set("IQ > ")
                        self.mask2_value.delete(0, END)
                        self.mask2_value.insert(0, '20000')

                        self.primary_cleanup_text.set("CI < ")
                        self.primary_cleanup_value.delete(0, END)
                        self.primary_cleanup_value.insert(0, '0.05')

                        self.secondary_cleanup_text.set("CI < ")
                        self.secondary_cleanup_value.delete(0, END)
                        self.secondary_cleanup_value.insert(0, '0.10')

                self.extension = list(set(extensions))[0]
                if self.gui_mode:
                    self.text.set('Selected Input Files: %d' % len(self.all_file_paths))
                    self.update_idletasks()
                self.load_method = 'files'

    def verifyFilePaths(self, file_paths):

        # Ensure that the file_paths are not a empty string and if so, convert to a list
        if not any([isinstance(file_paths, list), isinstance(file_paths, tuple)]):
            file_paths = [file_paths]

        # Check for spaces in filename
        verified_file_paths = []

        for fid in file_paths:
            file_path_contains_no_spaces = False
            file_path_exists = False

            if fid.find(' ') > 0:
                response = messagebox.showwarning(
                    title='Warning',
                    message="Spaces were detected in the input file paths. Please ensure that all spaces are removed prior to running Dream3d.",
                    type='ok',
                )
            else:
                file_path_contains_no_spaces = True

            if os.path.isfile(fid):
                file_path_exists = True

            if all([file_path_contains_no_spaces, file_path_exists]):
                verified_file_paths.append(fid)

        return verified_file_paths

    def onGenerateFiles(self):
        if hasattr(self, "file_paths") and hasattr(self, 'load_method'):
            if self.load_method == 'files':
                self.prepareInputs(files_already_exist=False)
                # Generate Input Files if User Hasn't Submitted Existing Files
                self.generateDream3dInputs()

            elif self.load_method == 'directory':
                response = messagebox.showwarning(
                    title='Warning',
                    message="To re-generate input files, please select ANG or CTF files using the top left button. Then hit 'Generate Input File(s)'.",
                    type='ok',
                )

        else:
            response = messagebox.showwarning(title='Warning', message="No input file(s) selected.", type='ok')
            pass

    def onLoadDirectory(self):
        self.file_paths = []
        options = dict(title='Select Parent Directory', initialdir='../', mustexist=True)
        directory = filedialog.askdirectory(**options)

        self.all_file_paths = glob.glob(os.path.join(directory, '*', '*.json'))
        self.file_paths = self.verifyFilePaths(self.all_file_paths)

        if len(self.file_paths):
            self.prepareInputs(files_already_exist=True)
            self.text.set(f'Found {len(self.file_paths)} Existing Input Files (Extension: {self.extension.upper()})')
            self.update_idletasks()
            self.load_method = 'directory'
        else:
            self.text.set('Found 0 Existing Input Files. Please provide a valid results directory.')
            self.update_idletasks()

    def prepareInputs(self, files_already_exist=False):
        # Load first file to check Dream3D version and file extension (.ang or .ctf)
        use_gui_inputs = False if files_already_exist else True
        self.getDream3DVersionAndFileExtension(use_gui_inputs=use_gui_inputs)

        if files_already_exist:
            parent_dir = os.path.dirname(os.path.dirname(self.file_paths[0]))
            file_ext = '.dream3d'

        else:
            parent_dir = os.path.join(os.path.dirname(self.file_paths[0]), self.entry1.get())
            file_ext = '.json'

        subdirectories = [os.path.basename(n).split('.')[0] for n in self.file_paths]

        # Modify output file paths for each EBSD scan
        output_file_paths = {}
        for subdir, oim_path in zip(subdirectories, self.file_paths):
            # Check for existing files here and only add valid files to the inputs dictionary if overwrite is allowed or files do not exist
            if self.int_overwrite.get() == 1 or not os.path.exists(
                os.path.join(parent_dir, subdir, subdir + file_ext).replace('\\', '/')
            ):

                output_file_paths[subdir] = dict(
                    input_path=oim_path,
                    raw_ipf_x=os.path.join(parent_dir, subdir, subdir + "_IPF_Raw_X.tif").replace('\\', '/'),
                    raw_ipf_y=os.path.join(parent_dir, subdir, subdir + "_IPF_Raw_Y.tif").replace('\\', '/'),
                    raw_ipf_z=os.path.join(parent_dir, subdir, subdir + "_IPF_Raw_Z.tif").replace('\\', '/'),
                    cleaned_ipf_x=os.path.join(parent_dir, subdir, subdir + "_IPF_Cleaned_X.tif").replace('\\', '/'),
                    cleaned_ipf_y=os.path.join(parent_dir, subdir, subdir + "_IPF_Cleaned_Y.tif").replace('\\', '/'),
                    cleaned_ipf_z=os.path.join(parent_dir, subdir, subdir + "_IPF_Cleaned_Z.tif").replace('\\', '/'),
                    average_ipf_x=os.path.join(parent_dir, subdir, subdir + "_IPF_Average_X.tif").replace('\\', '/'),
                    average_ipf_y=os.path.join(parent_dir, subdir, subdir + "_IPF_Average_Y.tif").replace('\\', '/'),
                    average_ipf_z=os.path.join(parent_dir, subdir, subdir + "_IPF_Average_Z.tif").replace('\\', '/'),
                    mtr_ipf_x=os.path.join(parent_dir, subdir, subdir + "_IPF_MTR_X.tif").replace('\\', '/'),
                    mtr_ipf_y=os.path.join(parent_dir, subdir, subdir + "_IPF_MTR_Y.tif").replace('\\', '/'),
                    mtr_ipf_z=os.path.join(parent_dir, subdir, subdir + "_IPF_MTR_Z.tif").replace('\\', '/'),
                    initial_pole_figure=os.path.join(parent_dir, subdir, 'PoleFigures').replace('\\', '/'),
                    final_pole_figure=os.path.join(parent_dir, subdir, 'PoleFigures').replace('\\', '/'),
                    mtr_pole_figure=os.path.join(parent_dir, subdir, 'PoleFigures').replace('\\', '/'),
                    dream3d=os.path.join(parent_dir, subdir, subdir + ".dream3d").replace('\\', '/'),
                    json_path=os.path.join(parent_dir, subdir, subdir + '.json'),
                )

        self.inputs = dict(
            output_folder_name=self.entry1.get(),
            caxis_misalignment=self.entry2.get(),
            mask1_value=self.mask1_value.get(),
            mask2_value=self.mask2_value.get(),
            primary_cleanup_value=self.primary_cleanup_value.get(),
            secondary_cleanup_value=self.secondary_cleanup_value.get(),
            min_mtr_size=self.entry4.get(),
            paths=output_file_paths,
            subdirectories=subdirectories,
            parent_directory=parent_dir,
            extension=self.extension,
        )

        # Create folder structure
        if not files_already_exist:
            setup_directories(parent_dir=self.inputs['parent_directory'], subdirectories=self.inputs['subdirectories'])

    def generateDream3dInputs(self):
        # Generate Input Files
        # if self.dream3d_version == 'version6.13': # Dream3D Version 6.13
        #     if 'ang' in self.inputs['extension'].lower():
        #         create_d3d_input_files_v613_ang(self.inputs)
        #     elif 'ctf' in self.inputs['extension'].lower():
        #         create_d3d_input_files_v613_ctf(self.inputs)

        if self.dream3d_version == 'version6.5':  # Dream3D Version 6.5
            if 'ang' in self.inputs['extension'].lower():
                create_d3d_input_files_v65_ang(self.inputs)
            elif 'ctf' in self.inputs['extension'].lower():
                create_d3d_input_files_v65_ctf(self.inputs)

        # Provide feedback to user
        if len(self.inputs['paths'].keys()):
            messagebox_type = messagebox.showinfo
        else:
            messagebox_type = messagebox.showwarning

        response = messagebox_type(
            title='Input File Status',
            message=f"{len(self.inputs['paths'].keys())} / {len(self.all_file_paths)} input files were successfully written, given the current overwrite settings.",
            type='ok',
        )

    def getLiveInstances(self, idname='PipelineRunner'):
        count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if idname.lower() in proc.info['name'].lower():
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return count

    def checkStatus(self, verbose=False):
        number_pipeline_runners_open = self.getLiveInstances()

        # Check for output files that should be written
        all_sample_names = list(self.inputs['paths'].keys())
        written_files = []
        for sample_name in all_sample_names:
            specified_dream3d_path = self.inputs['paths'][sample_name]['dream3d']
            written_files.append(os.path.exists(specified_dream3d_path))

        job_completion_status = False
        errors = False

        if all([number_pipeline_runners_open == 0, sum(written_files) == len(all_sample_names)]):
            job_completion_status = True

        elif number_pipeline_runners_open == 0 and sum(written_files) != len(all_sample_names):
            job_completion_status = False
            errors = True

        if verbose or job_completion_status or errors:
            print(
                f"\
                Dream3D: {self.dream3d_version}\n\
                Number of PipelineRunner instances: {number_pipeline_runners_open}\n\
                Number of Written or Existing Dream3D Files: {sum(written_files)}\n\
                Job Complete: {job_completion_status}\n\
                Dream3D Errors causing premature exiting of program?: {errors}\n\
                "
            )

        return job_completion_status

    def getDream3DVersionAndFileExtension(self, use_gui_inputs=True):
        if use_gui_inputs:
            if self.int_dream3d_version.get() == 1:
                self.dream3d_version = 'version6.13'
            elif self.int_dream3d_version.get() == 0:
                self.dream3d_version = 'version6.5'

            try:
                self.extension = self.file_paths[0].split('.')[-1]
            except:
                pass

        else:  # read in existing json file to determine path and dream3d version
            if len(self.file_paths):
                # Load first file to check extension
                with open(self.file_paths[0], 'r') as f:
                    inputfile = json.load(f)

                first_key = sorted(list(inputfile.keys()))[0]  # Some are '00' and others are '0'
                self.dream3d_version = 'version' + str(inputfile['PipelineBuilder']['Version'])

                # If correct dream3d version is not displayed, update radio buttons
                if self.dream3d_version == 'version6.13':
                    self.rbtn1.invoke()
                elif self.dream3d_version == 'version6.5':
                    self.rbtn2.invoke()

                self.extension = inputfile[first_key]['InputFile'].split('.')[-1]

                # self.update_idletasks()

    def loadPipelineRunnerPath(self):
        with open('../Templates/dream3d_config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        self.timeout_time = config['error_handling']['timeout_seconds']
        pipeline_runner_path = config['dream3d_pipeline_runner_location'][self.dream3d_version]

        return r"start " + pipeline_runner_path


class PipelineBuilderUI_PW9(GenericPipelineBuilderUI):
    def __init__(self, gui_mode=True):
        super().__init__(gui_mode=gui_mode)

    def onSubmit(self):

        if len(self.file_paths):
            self.submitDream3dJob()

            if self.int_overwrite.get() == 1 or len(self.outputs):

                # Once job status is complete, notify user and allow them to exit or remain to submit another job.
                response = messagebox.showinfo(
                    title='Status Update',
                    message="Dream3D runs have completed. Would you like to exit the program?.",
                    type='yesno',
                )
                if response == 'yes':
                    self.quit()
            else:
                response = messagebox.showinfo(
                    title='Dream3D Status',
                    message=f"Given the current settings, the program has not submitted the requested Dream3D jobs as this process would overwrite existing files.",
                    type='ok',
                )

        # No input files chosen....
        else:
            response = messagebox.showwarning(
                title='Warning',
                message="No input file(s) selected. Click YES to exit the program, or NO to keep interface open.",
                type='yesno',
            )
            if response == 'yes':
                self.quit()

    def submitDream3dJob(self):
        pipeline_runner_path = self.loadPipelineRunnerPath()
        self.outputs = []
        for key in self.inputs['paths'].keys():
            # Check to ensure overwriting is allowed or that the Dream3D files do not exist --> if so, submit job
            if self.int_overwrite.get() == 1 or not os.path.exists(self.inputs['paths'][key]['dream3d']):
                command = pipeline_runner_path + ' -p ' + self.inputs['paths'][key]['json_path']
                process = subprocess.Popen(command, shell=True)
                self.outputs.append(process)

        # After 5 seconds, check to see if either PipelineRunner is still running or output files have been written
        if self.int_overwrite.get() == 1 or len(self.outputs):
            time.sleep(5)
            t1 = time.time()
            self.status = self.checkStatus(verbose=False)

            # Loop to periodically check job status

            while not self.status:
                time.sleep(5)
                self.status = self.checkStatus(verbose=False)

                runtime_seconds = time.time() - t1
                if runtime_seconds > self.timeout_time:
                    break


class UserGuide(Frame):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        self.pack()

        frame1 = Frame(self)
        frame1.pack(fill=X)
        self.choice_text = StringVar()
        text = """

Microtexture Analysis User Guide

Automated routines were developed by Pratt & Whitney to process and quantify
microtexture in titanium. These routines were made available as part of the
PW9 program for AIPT assessment and publicly released under PW24 program.
The routines use open-source software Dream3D to perform EBSD file cleanup and
feature quantification. Additional post-processing scripts were developed in
Python to compute additional metrics and automate data post-processing. The
Python executables were created to 1) eliminate need to install software
requiring administrative privilege and 2) improve readability and
maintainability of code base

GETTING STARTED:

There are two main tabs near the top of the GUI called 'Pipeline Builder'
and 'Microtexture Analysis'.

Pipeline Builder: This tab allows the user to generate new input files
(.JSON) for Dream3D analysis or to load existing ones that may have already
been created.

To create new files, the user must select one or more ANG or CTF files using
the upper-left hand button. The number of selected files will be updated near
the top of the menu.  Next, the user must define the 'Output Folder Name',
which is a folder that will be created if not already present. Note: this can be a relative
path name like "Results", which will be created in the same folder as the
EBSD files. Otherwise, the user can provide a hard path
like "C:/Users/UserName/Desktop/Results" and the results will saved there
instead.

Next, users must define the C-axis misorientation threshold for
neighbor-to-neighbor grouping of pixels, based off c-axis misalignment. 20deg
is default. Smaller values produces finer, more highly aligned features.
Larger values will produce coarser features w/ larger internal
misorientation.

The threshold user-inputs are used to clean the EBSD data before segmenting
pixels into features. This is broken down into 3 stages:

    1) Determining "GOOD" vs. "BAD" data, where BAD data will be routed
       for subsequent cleanup. ANG data use a combination of Confidence Index (CI)
       and Image Quality (IQ). Default values for GOOD data are CI > 0.05 and
       IQ > 20000.

    2) Primary cleanup: takes place using the "Replace Element Attributes with Neighbor (Threshold)" filter.
       Data for pixels with values below the user-defined threshold are replaced
       with the data of their highest quality neighbor. This can be an aggressive
       cleanup filter depending on threshold value.

    3) Secondary cleanup: If addtional cleanup is desired, a more strict cleanup filter
       can be applied if the user-defined threshold values are greater than that used in the
       Primary cleanup step. This data is provided to the "Neighbor Orientation Correlation" filter,
       which will continue to clean low quality data if it has 3 neighbors and their orientation is
       within 5 deg of the reference pixel.

The default Dream3D version to run is version 6.5.49.

Entries are required for all the above when generating new input files
(using the bottom left button). A pop-up window will emerge if input file
(s) are written succesfully.

If the user would like to run or re-run input files that have already been
generated, the bottom-middle button should be used. The user will use the
File Explorer window to select the parent directory containing specimen
folders, which in turn contain the Dream3D input files(.JSON). If a parent
direcotry is selected correctly, the GUI will display how many JSON files
have been identified within the parent directory. The file extensions of the
EBSD data and the Dream3D version will also be inferred from the input file.

To submit jobs to Dream3D, the user will either have to first run 'Generate
Input File(s)' and then can hit the 'Submit to Dream3D' button. Otherwise,
the user can 'Load Existing Input File(s)' and then hit the 'Submit to
Dream3D' button. All input files will be submitted in parallel using
Dream3D's PipelineRunner executable. Please note that could cause memory
issues if trying to run too many jobs at once.

NOTES ON REFERENCE FRAMES:

Each SEM/EBSD vendor has different orientation reference frames. The tool
currently assumes EDAX data (.ANG) require a 90 degree Euler rotation about
[001] to align Euler and sample reference frame. The tool does not perform
any Euler rotations when processing Oxford .CTF files. It is the
responsibility of the users to verify and/or modify that these prescribed
sets of rotations are correct when deadling with your own datasets. These can
be accessed by opening the written DREAM.3D pipeline JSON files in a text
editor or using the DREAM.3D GUI. No sample reference frame rotations are applied
by default. The filters are in place for users to do so, by adding non-zero
rotation angles.

NOTES ON OUTPUTS:

IPF Maps:

The tool will generate X,Y,Z IPF maps for the raw data, cleaned data,
feature-averaged data and MTR data.


"""

        label6a = Text(self, wrap=WORD, width=100)
        label6a.insert(END, text)
        label6a.pack(in_=frame1, pady=10, padx=10, side=TOP, anchor=NW)
