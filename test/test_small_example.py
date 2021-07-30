"""Test the processing of a small dataset.

- Load a small dataset, in interleaved format.
- Add metadata, and split out a separate CognateTable and CognatesetTable.
- Add a LanguageTable and a ParameterTable for the concepts.
- Add segments
"""

import csv
import pytest
import logging
import tempfile
from pathlib import Path

from lexedata.importer import excel_interleaved
from lexedata.util.add_metadata import add_metadata

from mock_excel import MockSingleExcelSheet


@pytest.fixture
def interleaved_excel_example():
    data = [
        ["", "Duala", "Ntomba", "Ngombe", "Bushoong"],
        ["all", "ɓɛ́sɛ̃", "(nk)umá", "ńsò", "kim"],
        ["", "1", "9", "10", "11"],
        ["arm", "dia", "lobɔ́kɔ", "lò-bókò (PL: màbókò)", "lɔ̀ɔ́"],
        ["", "7", "1", "1", "1"],
        ["ashes", "mabúdú", "metókó", "búdùlù ~ pùdùlù", "bu-tók"],
        ["", "17", "16", "17", "16"],
        ["bark", "bwelé", "lopoho ~ mpoho ~ lòpòhó", "émpósù ~ ímpósù", "yooʃ"],
        ["", "23", "22", "22", "22"],
        ["belly", "dibum", "ikundú", "lì-bùmù", "ì-kù:n"],
        ["", "1", "18", "1", "18"],
        ["big", "éndɛ̃nɛ̀", "nɛ́nɛ́", "nɛ́nɛ ~ nɛ́nɛ́nɛ", "nɛ́n"],
        ["", "1", "1", "1", "1"],
        ["bird", "inɔ̌n", "mpulú", "é-mbùlù ~ í-mbùlù", "pul"],
        ["", "1", "7", "7", "7"],
        ["bite", "kukwa", "lamata", "kokala", "a-ʃum"],
        ["", "6", "2", "7", "1"],
        ["black", "wínda", "", "hínda; épííndu", "a-picy; ndwɛɛm"],
        ["", "21", "", "21, 21", "22, 23"],
    ]
    return MockSingleExcelSheet(data)


def test_interleaved(interleaved_excel_example):
    ids = set()
    ds = [
        dict(
            zip(
                ["ID", "Language_ID", "Concept_ID", "Form", "Comment", "Cognateset_ID"],
                row,
            )
        )
        for row in excel_interleaved.import_interleaved(
            interleaved_excel_example, logger=logging.Logger, ids=ids
        )
    ]
    assert len(list(ds)) == 37
    assert ids == {
        "bushoong_all",
        "bushoong_arm",
        "bushoong_ashes",
        "bushoong_bark",
        "bushoong_belly",
        "bushoong_big",
        "bushoong_bite",
        "bushoong_bird",
        "bushoong_black",
        "bushoong_black_s2",
        "duala_all",
        "duala_arm",
        "duala_ashes",
        "duala_bark",
        "duala_belly",
        "duala_big",
        "duala_bird",
        "duala_bite",
        "duala_black",
        "ngombe_all",
        "ngombe_arm",
        "ngombe_ashes",
        "ngombe_bark",
        "ngombe_belly",
        "ngombe_big",
        "ngombe_bird",
        "ngombe_bite",
        "ngombe_black",
        "ngombe_black_s2",
        "ntomba_all",
        "ntomba_arm",
        "ntomba_ashes",
        "ntomba_bark",
        "ntomba_belly",
        "ntomba_big",
        "ntomba_bird",
        "ntomba_bite",
    }


def test_create_wordlist(interleaved_excel_example):
    ids = set()
    forms = [
        dict(
            zip(
                ["ID", "Language_ID", "Concept_ID", "Form", "Comment", "Cognateset_ID"],
                row,
            )
        )
        for row in excel_interleaved.import_interleaved(
            interleaved_excel_example, logger=logging.Logger, ids=ids
        )
    ]
    path = Path(tempfile.mkdtemp())
    with (path / "forms.csv").open("w", encoding="utf8") as form_table_file:
        writer = csv.DictWriter(
            form_table_file,
            fieldnames=[
                "ID",
                "Language_ID",
                "Concept_ID",
                "Form",
                "Comment",
                "Cognateset_ID",
            ],
        )
        writer.writeheader()
        writer.writerows(forms)
    ds = add_metadata(path / "forms.csv")
    ds.write_metadata(path / "Wordlist-metadata.json")
    assert {f.name for f in path.iterdir()} == {"forms.csv", "Wordlist-metadata.json"}
    assert len(ds.tables) == 1, "Expected a single table"
    assert [c.name for c in ds["FormTable"].tableSchema.columns] == [
        "ID",
        "Language_ID",
        "Concept_ID",
        "Form",
        "Comment",
        "Cognateset_ID",
        "Segments",
        "Source",
    ]
