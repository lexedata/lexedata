# -*- coding: utf-8 -*-
import typing as t
import urllib.parse
from pathlib import Path

import pycldf
import openpyxl as op

from lexedata import types

WARNING = "\u26A0"

# ----------- Remark: Indices in excel are always 1-based. -----------

# TODO: Make comments on Languages, Cognatesets, and Judgements appear as notes
# in Excel.

# TODO: cProfile – where's the bottleneck that makes this run so slow? It looks
# like it is the actual saving of the dataset. Check again whether we can use
# https://openpyxl.readthedocs.io/en/stable/optimized.html#write-only-mode and
# whether it's nicely faster.


class ExcelWriter:
    """Class logic for cognateset Excel export."""

    header = [("ID", "CogSet")]  # Add columns here for other datasets.

    def __init__(
        self, dataset: pycldf.Dataset, url_base: t.Optional[str] = None, **kwargs
    ):
        self.dataset = dataset
        if url_base:
            self.URL_BASE = url_base
        else:
            self.URL_BASE = "https://example.org/{:s}"

    def set_header(self):
        c_id = self.dataset["CognatesetTable", "id"].name
        try:
            c_comment = self.dataset["CognatesetTable", "comment"].name
        except KeyError:
            c_comment = None
        self.header = []
        for column in self.dataset["CognatesetTable"].tableSchema.columns:
            if column.name == c_id:
                self.header.insert(0, (c_id, "CogSet"))
            elif column.name == c_comment:
                continue
            else:
                self.header.append((column.name, column.name))

    def create_excel(
        self, out: Path, size_sort: bool = False, language_order="name"
    ) -> None:
        """Convert the initial CLDF into an Excel cognate view

        The Excel file has columns "CogSet", one column each mirroring the
        other cognateset metadata, and then one column per language.

        The rows contain cognate data. If a language has multiple reflexes in
        the same cognateset, these appear in different cells, one below the
        other.

        Parameters
        ==========
        out: The path of the Excel file to be written.

        size_sort: If true, cognatesets are ordered by the number of cognates
            corresponding to the cognateset

        language_order: column name, languages appear ordered by given column name from
            LanguageTable

        """
        # TODO: Check whether openpyxl.worksheet._write_only.WriteOnlyWorksheet
        # will be useful (maybe it's faster or prevents us from some mistakes)?
        # https://openpyxl.readthedocs.io/en/stable/optimized.html#write-only-mode
        wb = op.Workbook()
        ws: op.worksheet.worksheet.Worksheet = wb.active

        # Define the columns
        self.lan_dict: t.Dict[str, int] = {}
        excel_header = [name for cldf, name in self.header]

        c_name = self.dataset["LanguageTable", "name"].name
        c_id = self.dataset["LanguageTable", "id"].name
        if language_order:
            c_sort = self.dataset["LanguageTable", f"{language_order}"].name
            languages = sorted(
                self.dataset["LanguageTable"], key=lambda x: x[c_sort], reverse=False
            )
        else:
            languages = self.dataset["LanguageTable"]
        for col, lan in enumerate(languages, len(excel_header) + 1):
            self.lan_dict[lan[c_id]] = col
            excel_header.append(lan[c_name])

        ws.append(excel_header)

        c_form_id = self.dataset["FormTable", "id"].name
        all_forms = {f[c_form_id]: f for f in self.dataset["FormTable"]}
        all_judgements = {}

        c_cognateset = self.dataset["CognateTable", "cognatesetReference"].name
        for j in self.dataset["CognateTable"]:
            all_judgements.setdefault(j[c_cognateset], []).append(j)
        # TODO: If there is no cognateset table, add one – actually, that
        # should happen in the importer, the export should not modify the
        # dataset!!
        try:
            c_comment = self.dataset["CognatesetTable", "comment"].name
        except KeyError:
            c_comment = None
        c_cogset_id = self.dataset["CognatesetTable", "id"].name
        # Iterate over all cognate sets, and prepare the rows.
        # Again, row_index 2 is indeed row 2
        row_index = 1 + 1

        if size_sort:
            cogsets = sorted(
                self.dataset["CognatesetTable"],
                key=lambda x: len(all_judgements[x[c_cogset_id]]),
                reverse=True,
            )
        else:
            cogsets = self.dataset["CognatesetTable"]

        for cogset in cogsets:
            # possible a cogset can appear without any judgment, if so ignore it
            if cogset[c_cogset_id] not in all_judgements:
                continue
            # In a write-only workbook, rows can only be added with append().
            # It is not possible to write (or read) cells at arbitrary
            # locations with cell() or iter_rows(). -> We want to use the speed
            # of a writeonly workbook, so we should build the sheet row-by-row.

            # Put the cognateset's tags in column B.
            new_row_index = self.create_formcells_for_cogset(
                all_judgements[cogset[c_cogset_id]], ws, all_forms, row_index
            )

            for row in range(row_index, new_row_index):
                for col, (db_name, header) in enumerate(self.header, 1):
                    column = self.dataset["CognatesetTable", db_name]
                    if column.separator is None:
                        value = cogset[db_name]
                    else:
                        value = column.separator.join([str(v) for v in cogset[db_name]])
                    cell = ws.cell(row=row, column=col, value=value)
                    # Transfer the cognateset comment to the first Excel cell.
                    if c_comment and col == 1 and cogset.get(c_comment):
                        cell.comment = op.comments.Comment(
                            cogset["Comment"], __package__
                        )

            row_index = new_row_index
        wb.save(filename=out)

    def create_formcells_for_cogset(
        self,
        cogset: types.CogSet,
        ws: op.worksheet.worksheet.Worksheet,
        all_forms: t.Dict[str, types.Form],
        row_index: int,
    ) -> int:
        """Writes all forms for given cognate set to Excel.

        Take all forms for a given cognate set as given by the database, create
        a hyperlink cell for each form, and write those into rows starting at
        row_index.

        Return the row number of the first empty row after this cognate set,
        which can then be filled by the following cognate set.

        """
        c_form = self.dataset["CognateTable", "formReference"].name
        c_language = self.dataset["FormTable", "languageReference"].name
        # Read the forms from the database and group them by language
        forms = t.DefaultDict[int, t.List[types.Form]](list)
        for judgement in cogset:
            form_id = judgement[c_form]
            form = all_forms[form_id]
            forms[self.lan_dict[form[c_language]]].append((form, judgement))

        if not forms:
            return row_index + 1

        # maximum of rows to be added
        maximum_cogset = max([len(c) for c in forms.values()])
        for column, cells in forms.items():
            for row, judgement in enumerate(cells, row_index):
                self.create_formcell(judgement, ws, column, row)
        # increase row_index and return
        row_index += maximum_cogset

        return row_index

    def create_formcell(
        self, judgement, ws: op.worksheet.worksheet.Worksheet, column: int, row: int
    ) -> None:
        """Fill the given cell with the form's data.

        In the cell described by ws, column, row, dump the data for the form:
        Write into the the form data, and supply a comment from the judgement
        if there is one.

        """
        # TODO: Use CLDF terms instead of column names, like the c_ elsewhere
        cell_value = self.form_to_cell_value(judgement[0], judgement[1])
        form_cell = ws.cell(row=row, column=column, value=cell_value)
        c_id = self.dataset["FormTable", "id"].name
        comment = judgement[1].get("comment", None)
        if comment:
            form_cell.comment = op.comments.Comment(comment, __package__)
        link = self.URL_BASE.format(urllib.parse.quote(judgement[0][c_id]))
        form_cell.hyperlink = link

    def form_to_cell_value(self, form: types.Form, meta: types.Judgement) -> str:
        """Build a string describing the form itself

        Provide the best transcription and all translations of the form strung
        together.

        k a w e n a t j a k a
        d i +dúpe
        +iíté+ k h ú
        tákeː+toː
        h o n _tiem_litimuleni
        hont i e m _litimuleni
        """
        segments = self.get_segments(form)
        if segments is None:
            return form["Form"]
        transcription = ""
        old_end = 0
        if not meta.get("Segment_Slice"):
            meta["Segment_Slice"] = ["0:{:d}".format(len(segments))]
        for startend in meta["Segment_Slice"]:
            start, end = startend.split(":")
            start = int(start)
            end = int(end)
            transcription += "".join(s[0] for s in segments[old_end:start])
            transcription += "{ "
            transcription += " ".join(segments[start:end])
            # TODO: Find a sensible way to split the alignments instead – this
            # is trivial for a single segment slice, but requires some fiddling
            # for split morphemes.
            transcription += " }"
            old_end = end
        transcription += "".join(s[0] for s in segments[old_end : len(segments) + 1])
        transcription = transcription.strip()
        translations = []

        suffix = ""
        try:
            c_comment = self.dataset["FormTable", "comment"].name
            if form.get(c_comment):
                suffix = f" {WARNING:}"
        except KeyError:
            pass

        # corresponding concepts
        # (multiple concepts) and others (single concept)
        c_concept = self.dataset["FormTable", "parameterReference"].name
        if isinstance(form[c_concept], list):
            for f in form[c_concept]:
                translations.append(f)
        else:
            translations.append(form[c_concept])
        return "{:} ‘{:}’{:}".format(transcription, ", ".join(translations), suffix)

    def get_segments(self, form):
        c_segments = self.dataset["FormTable", "Segments"].name
        return form[c_segments]


# TODO: Somehow, this script tends to run very slowly. Find the bottleneck, and
# see whether we can get it to speed up to seconds, not minutes!
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Create an Excel cognate view from a CLDF dataset"
    )
    parser.add_argument(
        "--metadata",
        help="Path to metadata file for dataset input",
        default="Wordlist-metadata.json",
    )
    parser.add_argument(
        "--excel", help="Excel output file path", default="Cognates.xlsx"
    )
    parser.add_argument(
        "--size-sort",
        action="store_true",
        default=False,
        help="List the biggest cognatesets first",
    )
    parser.add_argument(
        "--language-sort-column", help="A column name to sort languages by"
    )
    parser.add_argument(
        "--url-template",
        help="A template string for URLs pointing to individual forms. For example, to"
        " point to lexibank, you would use https://lexibank.clld.org/values/{:}."
        " (default: https://example.org/lexicon/{:})",
    )
    # TODO: Derive URL template from the "special:domain" property of the
    # wordlist, where it exists? So something like
    # 'https://{special:domain}/values/{{:}}'? It would work for Lexibank and
    # for LexiRumah, is it robust enough?
    args = parser.parse_args()
    E = ExcelWriter(pycldf.Wordlist.from_metadata(args.metadata))
    E.set_header()
    E.create_excel(
        args.excel, size_sort=args.size_sort, language_order=args.language_sort_column
    )
