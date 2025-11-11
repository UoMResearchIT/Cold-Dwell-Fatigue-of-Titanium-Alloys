import unittest
import glob
import json
import os
import shutil
import pandas as pd
import numpy as np
from forms import PipelineBuilderUI_PW9


class UnitTests(unittest.TestCase):
    """
    A testcase is created by subclassing unittest.TestCase.
    Individual tests are defined with methods whose names start with the letters 'test'. This naming convention informs the test runner about which methods represent tests.
    """

    def setUp(self):
        self.app = PipelineBuilderUI_PW9(gui_mode=False)

    def tearDown(self):
        self.app.quit()

    # @unittest.expectedFailure
    # def test_fail(self):
    #     self.assertEqual(1, 0, "broken")

    def test1(self):
        """
        Verifies that the tool
        """
        files = [r'../Sample_ANG_Files/PW9-Sample-Small.ang']
        self.app.onLoadFiles(all_file_paths=files)
        self.assertEqual(len(files), len(self.app.file_paths))


if __name__ == '__main__':
    unittest.main()
