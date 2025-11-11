# -*- mode: python ; coding: utf-8 -*-

import sys
sys.path.append('.')
import __init__
version = __init__.__version__

block_cipher = None

a = Analysis(['gui.py'], hiddenimports = ["skimage.filters.edges"], pathex=['.'])
#hidden imports added to above because it would throw an Module import error for the skimage.filters.edge module...

#b = Analysis(['microtexture_analysis.py'], hiddenimports = ["skimage.filters.edges"], pathex=['.'])
#hidden imports added to above because it would throw an Module import error for the skimage.filters.edge module...

a_name = 'ti-microtexture-analysis' + '-v' + version
#b_name = 'microtexture-analysis' + '-v' + version

#MERGE((b, b_name, b_name), (a, a_name, a_name))

a_pyz = PYZ(a.pure)
a_exe = EXE(a_pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          a.dependencies,
          name=a_name,
          debug = False,
          strip=False,
          console=True)

# b_pyz = PYZ(b.pure)
# b_exe = EXE(b_pyz,
#           b.scripts,
#           b.binaries,
#           b.zipfiles,
#           b.datas,  
#           b.dependencies,
#           name=b_name,
#           strip=False,
#           debug=False,
#           console=True)