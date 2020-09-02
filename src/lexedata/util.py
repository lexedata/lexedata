# -*- coding: utf-8 -*-
import re
from pathlib import Path

import unicodedata
import unidecode as uni
import typing as t
import openpyxl as op

invalid_id_elements = re.compile(r"\W+")


def string_to_id(string: str) -> str:
    """Generate a useful id string from the string

    >>> string_to_id("trivial")
    'trivial'
    >>> string_to_id("Just 4 non-alphanumerical characters.")
    'just_4_non_alphanumerical_characters'
    >>> string_to_id("Это русский.")
    'eto_russkii'
    >>> string_to_id("该语言有一个音节。")
    'gai_yu_yan_you_yi_ge_yin_jie'
    >>> string_to_id("この言語には音節があります。")
    'konoyan_yu_nihayin_jie_gaarimasu'

    """
    # We nee to run this through valid_id_elements twice, because some word
    # characters (eg. Chinese) are unidecoded to contain non-word characters.
    # the japanese ist actually decoded incorrectly
    return invalid_id_elements.sub(
        "_", uni.unidecode(
            invalid_id_elements.sub("_", string)).lower()).strip("_")


def clean_cell_value(cell: op.cell.cell.Cell):
    if cell.value is None:
        return ''
    v = unicodedata.normalize('NFKD', (cell.value or '').strip())
    if type(v) == float:
        if v == int(v):
            return int(v)
        return v
    if type(v) == int:
        return v
    try:
        return v.replace("\n", ";\t")
    except TypeError:
        return str(v)


def get_cell_comment(cell: op.cell.Cell) -> t.Optional[str]:
    return cell.comment.text.strip() if cell.comment else ""


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("file", nargs="+", type=Path)
    args = parser.parse_args()
    for file in args.file:
        content = file.open().read()
        file.open("w").write(
            unicodedata.normalize('NFKD', content))

