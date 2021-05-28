import typing as t
import openpyxl as op
import unicodedata


def clean_cell_value(cell: op.cell.cell.Cell):
    if cell.value is None:
        return ""
    if type(cell.value) == float:
        if cell.value == int(cell.value):
            return int(cell.value)
        return cell.value
    elif type(cell.value) == int:
        return cell.value
    v = unicodedata.normalize("NFC", (cell.value or "").strip())
    try:
        return v.replace("\n", ";\t")
    except TypeError:
        return str(v)


def get_cell_comment(cell: op.cell.Cell) -> str:
    """Get the comment of a cell.

    Get the normalized comment of a cell: Guaranteed to be a string (empty if
    no comment), with lines joined by spaces instead and all 'lexedata' author
    annotations stripped.


    >>> from openpyxl.comments import Comment
    >>> wb = op.Workbook()
    >>> ws = wb.active
    >>> ws["A1"].comment = Comment('''This comment
    ... contains a linebreak and a signature.
    ...   -lexedata.exporter''',
    ... 'lexedata')
    >>> get_cell_comment(ws["A1"])
    'This comment contains a linebreak and a signature.'
    >>> get_cell_comment(ws["A2"])
    ''
    """
    raw_comment = cell.comment.text.strip() if cell.comment else ""
    lines = [
        line for line in raw_comment.split("\n") if line.strip() != "-lexedata.exporter"
    ]
    return " ".join(lines)


def normalize_header(row: t.Iterable[op.cell.Cell]) -> t.Iterable[str]:
    header = [unicodedata.normalize("NFKC", (n.value or "").strip()) for n in row]
    header = [h.replace(" ", "_") for h in header]
    header = [h.replace("(", "") for h in header]
    header = [h.replace(")", "") for h in header]

    return header
