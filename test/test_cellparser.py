# -*- coding: utf-8 -*-

from cellparser import Cellparser
from unittest import TestCase, TestSuite, TextTestRunner

class TestCellparser(TestCase):

    def setUp(self, file="test_cellparser.xlsx"):
        # set path and check for existing excel test file
        file = Path.cwd() / "initial_data" / file
        if not file.exists():
            print("There are no test files provided")
            exit()
        # open excel file and set iterators
        wb = op.load_workbook(filename=file)
        sheets = wb.sheetnames
        wb = wb[sheets[0]]
        iter_forms = wb.iter_rows(min_row=3, min_col=7)  # iterates over rows with forms
        iter_concept = wb.iter_rows(min_row=3, max_col=6)  # iterates over rows with concepts
        iter_lan = wb.iter_cols(min_row=1, max_row=2, min_col=7)




