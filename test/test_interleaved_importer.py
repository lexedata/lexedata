import openpyxl as op
from lexedata.importer.excel_interleaved import import_interleaved


def test_interleaved_import_skips_na():
    data = [
        ["", "l1", "l2"],
        ["all", "one form", "more, than, one, form"],
        ["", "1", "2"],
        ["arm", "matching, forms", "one form"],
        ["", "1, 2", "1, 2, 3"],
    ]

    # create excel with data
    wb = op.Workbook()
    ws = wb.active
    for row in data:
        ws.append(row)
    # import excel
    forms = [tuple(r) for r in import_interleaved(ws)]

    assert forms == [
        ("l1_all", "l1", "all", "one form", None, "1"),
        ("l1_arm", "l1", "arm", "matching", None, "1"),
        ("l1_arm_s2", "l1", "arm", "forms", None, "2"),
        ("l2_all", "l2", "all", "more", None, "2"),
        ("l2_all_s2", "l2", "all", "than", None, "2"),
        ("l2_all_s3", "l2", "all", "one", None, "2"),
        ("l2_all_s4", "l2", "all", "form", None, "2"),
        ("l2_arm", "l2", "arm", "one form", None, "1"),
        ("l2_arm_s2", "l2", "arm", None, None, "2"),
        ("l2_arm_s3", "l2", "arm", None, None, "3"),
    ]
