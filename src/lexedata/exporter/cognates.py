# -*- coding: utf-8 -*-
import typing as t
import urllib.parse
from pathlib import Path
from collections import OrderedDict, defaultdict

import pycldf
import openpyxl as op

from lexedata import types
import lexedata.cldf.db as db

WARNING = "\u26A0"

# ----------- Remark: Indices in excel are always 1-based. -----------

# TODO: ExcelWrite still uses SQLAlchemy, which we have nearly completely taken
# out. Rewrite those bits and get it to work – It's probably worth thinking
# about doing this without touching the database at all, and just work on the
# iterators like dataset[FormTable'], because here we don't need the smart
# lookup capabilities of the database to match similar forms. (Or do we?)

# TODO: Make comments on Languages, Cognatesets, and Judgements appear as notes
# in Excel.

# TODO: cProfile – where's the bottleneck that makes this run so slow? It looks
# like it is the actual saving of the dataset. Check again whether we can use
# https://openpyxl.readthedocs.io/en/stable/optimized.html#write-only-mode and
# whether it's nicely faster.

class ExcelWriter():
    """Class logic for cognateset Excel export."""
    header = [("ID", "CogSet")]  # Add columns here for other datasets.

    def __init__(self, dataset: pycldf.Dataset,
                 url_base: t.Optional[str] = None, **kwargs):
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
            self,
            out: Path,
            size_sort: bool = False,
            language_order="cldf_name"
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

        """
        # TODO: Check whether openpyxl.worksheet._write_only.WriteOnlyWorksheet
        # will be useful (maybe it's faster or prevents us from some mistakes)?
        # https://openpyxl.readthedocs.io/en/stable/optimized.html#write-only-mode
        wb = op.Workbook()
        ws: op.worksheet.worksheet.Worksheet = wb.active

        # Define the columns
        self.lan_dict: t.Dict[str, int] = {}
        excel_header = [name for cldf, name in self.header]
        # TODO: Sort languages by the language_order column – and clarify in
        # the docstring of this function whether we accept SQLite column names
        # (`cldf_name`), CLDF column names (`Name` or `Language`) or CLDF
        # property terms (`name` or
        # ``https://cldf.clld.org/v1.0/terms.rdf#name`). We can probably take
        # CLDF names and terms, because we can get them from the table as
        # c_sort = self.dataset[…]
        c_name = self.dataset["LanguageTable", "name"].name
        c_id = self.dataset["LanguageTable", "id"].name
        for col, lan in enumerate(
                self.dataset["LanguageTable"],
                len(excel_header) + 1):
            self.lan_dict[lan[c_id]] = col
            excel_header.append(lan[c_name])
        # TODO: Test the sorting.

        ws.append(excel_header)

        c_form_id = self.dataset["FormTable", "id"].name
        all_forms = {f[c_form_id]: f
                     for f in self.dataset["FormTable"]}
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
            cogsets = sorted(self.dataset['CognatesetTable'],
                             key=lambda x: len(all_judgements[x[c_cogset_id]]),
                             reverse=True)
        else:
            cogsets = self.dataset['CognatesetTable']
        for cogset in cogsets:
            # Put the cognateset's tags in column B.
            for col, (db_name, header) in enumerate(self.header, 1):
                column = self.dataset["CognatesetTable", db_name]
                if column.separator is None:
                    value = cogset[db_name]
                else:
                    value = column.separator.join([str(v) for v in cogset[db_name]])
                cell = ws.cell(row=row_index, column=col,
                               value=value)
                # Transfer the cognateset comment to the first Excel cell.
                if c_comment and col == 1 and cogset[c_comment]:
                    cell.comment = op.comments.Comment(
                        cogset.cldf_comment, __package__)

            new_row_index = self.create_formcells_for_cogset(
                all_judgements[cogset[c_cogset_id]], ws, all_forms, row_index, self.lan_dict)
            row_index = new_row_index
        wb.save(filename=out)

    def create_formcells_for_cogset(
            self,
            cogset: types.CogSet,
            ws: op.worksheet.worksheet.Worksheet,
            all_forms: t.Dict[str, types.Form],
            row_index: int,
            # FIXME: That's not just a str, it's a language_id, but String()
            # alias Language.id.type is not a Type, according to `typing`.
            lan_dict: t.Dict[str, int]) -> int:
        """Writes all forms for given cognate set to Excel.

        Take all forms for a given cognate set as given by the database, create
        a hyperlink cell for each form, and write those into rows starting at
        row_index.

        Return the row number of the first empty row after this cognate set,
        which can then be filled by the following cognate set.

        """
        c_cogset = self.dataset["CognateTable", "cognatesetReference"].name
        c_form = self.dataset["CognateTable", "formReference"].name
        c_language = self.dataset["FormTable", "languageReference"].name
        # Read the forms from the database and group them by language
        forms = t.DefaultDict[int, t.List[types.Form]](list)
        for judgement in cogset:
            form_id = judgement[c_form]
            form = all_forms[form_id]
            forms[self.lan_dict[form[c_language]]].append(
                (form, judgement))

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
            self,
            judgement,
            ws: op.worksheet.worksheet.Worksheet,
            column: int,
            row: int) -> None:
        """Fill the given cell with the form's data.

        In the cell described by ws, column, row, dump the data for the form:
        Write into the the form data, and supply a comment from the judgement
        if there is one.

        """
        # TODO: Use CLDF terms instead of column names, like the c_ elsewhere
        cell_value = self.form_to_cell_value(judgement[0])
        form_cell = ws.cell(row=row, column=column, value=cell_value)
        comment = judgement[1].get("Comment", None)
        if comment:
            form_cell.comment = op.comments.Comment(comment, __package__)
        link = self.URL_BASE.format(urllib.parse.quote(judgement[0]['ID']))
        form_cell.hyperlink = link

    def form_to_cell_value(self, form: types.Form) -> str:
        """Build a string describing the form itself

        Provide the best transcription and all translations of the form strung
        together.

        """

        transcription = self.get_best_transcription(form)
        translations = []

        suffix = ""
        # TODO: Use CLDF terms instead of column names, like the c_ elsewhere
        if form.get("Comment"):
            suffix = f" {WARNING:}"

        # corresponding concepts – TODO: distinguish between list data type
        # (multiple concepts) and others (single concept)
        c_concept = self.dataset["FormTable", "parameterReference"].name
        translations.append(form[c_concept])

        return "{:} ‘{:}’{:}".format(
            transcription, ", ".join(translations), suffix)

    #def get_best_transcription(self, form):
    #    if form.phonemic:
    #        return form.phonemic
    #    elif form.phonetic:
    #        return form.phonetic
    #    elif form.orthographic:
    #        return form.orthographic
    #    else:
    #        ValueError(f"Form {form:} has no transcriptions.")

    def get_best_transcription(self, form):
        # TODO: Use CLDF terms instead of column names, like the c_ elsewhere
        return form["FUN"]


# TODO: Somehow, this script tends to run very slowly. Find the bottleneck, and
# see whether we can get it to speed up to seconds, not minutes!
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Create an Excel cognate view from a CLDF dataset")
    parser.add_argument("--metadata", help="Path to metadata file for dataset input",
                        default="Wordlist-metadata.json")
    parser.add_argument("--excel", help="Excel output file path",
                        default="Cognates.xlsx")
    parser.add_argument(
        "--size-sort",
        action="store_true",
        default=False,
        help="List the biggest cognatesets first")
    parser.add_argument("--language-sort-column", help="A column name to sort languages by")
    parser.add_argument("--url-template", help="A template string for URLs pointing to individual forms. For example, to point to lexibank, you would use https://lexibank.clld.org/values/{:}. (default: https://example.org/lexicon/{:})")
    # TODO: Derive URL template from the "special:domain" property of the
    # wordlist, where it exists? So something like
    # 'https://{special:domain}/values/{{:}}'? It would work for Lexibank and
    # for LexiRumah, is it robust enough?
    args = parser.parse_args()
    E = ExcelWriter(pycldf.Wordlist.from_metadata(args.metadata))
    E.set_header()
    E.create_excel(args.excel, size_sort=args.size_sort)
