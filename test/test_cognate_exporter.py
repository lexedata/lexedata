import re
import logging
from pathlib import Path

import openpyxl as op
import tempfile

from lexedata.util.fs import get_dataset
from lexedata.exporter.cognates import ExcelWriter


def test_adding_singleton_cognatesets(caplog):
    dataset = get_dataset(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    with caplog.at_level(logging.WARNING):
        excel_writer = ExcelWriter(dataset=dataset, singleton_cognate=True)
        output = dirname / "out.xlsx"
        excel_writer.create_excel(out=output, status_update="(ignored)")
    assert re.search("no Status_Column to write", caplog.text)

    # load central concepts from output
    ws = op.load_workbook(output).active
    cogset_index = 0
    for row in ws.iter_rows(min_row=1, max_row=1):
        for cell in row:
            if cell.value == "CogSet":
                cogset_index = cell.column
    # when accessing the row as a tuple the index is not 1-based as for excel sheets
    cogset_ids = [row[cogset_index - 1].value for row in ws.iter_rows(min_row=2)]
    assert cogset_ids == [
        "one1",
        "one1",
        "one2",
        "one6",
        "two1",
        "three1",
        "two8",
        "three9",
        "four1",
        "four8",
        "five5",
        "X1_old_paraguayan_guarani",
        "X2_paraguayan_guarani",
        "X3_ache",
    ]
