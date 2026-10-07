import re

from lexedata import util, cli
from mock_excel import MockSingleExcelSheet

from lexedata.importer.cognates import import_cognates_from_excel


def test_alignment_in_cognate_excel_import():
    ds = util.fs.new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Language_ID": "lang",
                "Parameter_ID": "concept",
                "Form": "f",
                "value": "f",
            }
        ],
        CognatesetTable=[
            {"ID": "s1", "Source": "3", "Description": "A"},
        ],
        CognateTable=[
            {"ID": f"{i}{n}", "Cognateset_ID": f"s{i}", "Form_ID": "f1"}
            for i in range(1, 6)
            for n in range(i)
        ],
        LanguageTable=[{"ID": "lang", "Name": "Lang"}],
    )
    ds.add_columns("CognatesetTable", "comment")

    excel = MockSingleExcelSheet(
        [
            ["id", "Lang"],
            ["s1", "f { o - r m }"],
        ]
    )
    excel.cell(row=2, column=2).hyperlink = "/f1"

    import_cognates_from_excel(
        ws=excel,
        dataset=ds,
        extractor=re.compile("/(?P<ID>[^/]*)/?$"),
        logger=cli.logger,
    )

    assert list(ds["CognateTable"]) == [
        {
            "ID": "f1-s1",
            "Form_ID": "f1",
            "Cognateset_ID": "s1",
            "Segment_Slice": ["2:4"],
            "Alignment": ["o", "-", "r", "m"],
            "Source": [],
        }
    ]
