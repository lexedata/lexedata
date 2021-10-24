# -*- coding: utf-8 -*-
import re
import typing as t
import urllib.parse
from pathlib import Path
import traceback

import pycldf
import openpyxl as op

from lexedata import types
from lexedata import cli
from lexedata.util import parse_segment_slices

WARNING = "\u26A0"

# ----------- Remark: Indices in excel are always 1-based. -----------

# TODO: Make comments on Languages, Cognatesets, and Judgements appear as notes
# in Excel.

# Type aliases, for clarity
CognatesetID = str


class ExcelWriter:
    """Class logic for cognateset Excel export."""

    header: t.List[t.Tuple[str, str]]

    def __init__(
        self,
        dataset: pycldf.Dataset,
        database_url: t.Optional[str] = None,
        singleton_cognate: bool = False,
    ):
        self.dataset = dataset
        # assert that all required tables are present in Dataset
        try:
            for _ in dataset["CognatesetTable"]:
                break
        except (KeyError, FileNotFoundError):
            cli.Exit.INVALID_DATASET(
                "This script presupposes a separate CognatesetTable. Call `lexedata.edit.add_table CognatesetTable` to automatically add one."
            )
        try:
            for _ in dataset["CognateTable"]:
                break
        except (KeyError, FileNotFoundError):
            cli.Exit.NO_COGNATETABLE(
                "This script presupposes a separate CognateTable. Call `lexedata.edit.add_cognate_table` to automatically add one."
            )
        self.singleton = singleton_cognate
        self.set_header()
        if database_url:
            self.URL_BASE = database_url
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
        cogset_order: t.Optional[str] = None,
        language_order="name",
        status_update: t.Optional[str] = None,
        logger: cli.logging.Logger = cli.logger,
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

        status_update: string, writen to status_column of singleton cognates.

        """
        # cldf names
        try:
            c_name = self.dataset["LanguageTable", "name"].name
            c_id = self.dataset["LanguageTable", "id"].name
            c_form_id = self.dataset["FormTable", "id"].name
            c_language = self.dataset["FormTable", "languageReference"].name
            c_form_concept_reference = self.dataset[
                "FormTable", "parameterReference"
            ].name
            c_cognate_cognateset = self.dataset[
                "CognateTable", "cognatesetReference"
            ].name
            c_cognate_form = self.dataset["CognateTable", "formReference"].name
            c_cogset_id = self.dataset["CognatesetTable", "id"].name
            c_cogset_name = self.dataset["CognatesetTable", "name"].name
        except KeyError:
            formatted_lines = traceback.format_exc().splitlines()
            match = re.match(r'.*"(.*?)", "(.*?)".*', formatted_lines[2])
            cli.Exit.INVALID_COLUMN_NAME(
                f"The {match.group(1)} is missing the column {match.group(2)} which is required by cldf."
            )
        try:
            c_comment = self.dataset["CognatesetTable", "comment"].name
        except KeyError:
            c_comment = None

        wb = op.Workbook()
        ws: op.worksheet.worksheet.Worksheet = wb.active
        if status_update is not None:
            if ("Status_Column", "Status_Column") not in self.header:
                logger.warning(
                    f"You requested that I set the status of new singleton cognate sets to {status_update}, but your CognatesetTable has no Status_Column to write it to. If you want a Status "
                )
        # Define the columns, i.e. languages and write to excel
        self.lan_dict: t.Dict[str, int] = {}
        excel_header = [name for cldf, name in self.header]
        if language_order:
            c_sort = self.dataset["LanguageTable", f"{language_order}"].name
            languages = sorted(
                self.dataset["LanguageTable"], key=lambda x: x[c_sort], reverse=False
            )
        else:
            # sorted returns a list, so better return a list here as well
            languages = list(self.dataset["LanguageTable"])
        for col, lan in cli.tq(
            enumerate(languages, len(excel_header) + 1),
            task="Writing languages to excel header",
            total=len(languages),
        ):
            self.lan_dict[lan[c_id]] = col
            excel_header.append(lan[c_name])
        ws.append(excel_header)

        # load all forms
        all_forms = {f[c_form_id]: f for f in self.dataset["FormTable"]}

        # map form_id to id of associated concept
        concept_id_by_form_id = dict()
        for f in self.dataset["FormTable"]:
            concept = f[c_form_concept_reference]
            if isinstance(concept, str):
                concept_id_by_form_id[f[c_form_id]] = concept
            else:
                concept_id_by_form_id[f[c_form_id]] = concept[0]

        # load all cognates by cognateset id
        all_judgements: t.Dict[CognatesetID, t.List[types.CogSet]] = {}
        for j in self.dataset["CognateTable"]:
            all_judgements.setdefault(j[c_cognate_cognateset], []).append(j)

        # Again, row_index 2 is indeed row 2, row 1 is header
        row_index = 1 + 1
        cogsets = list(self.dataset["CognatesetTable"])
        # Sort first by size, then by the specified column, so that if both
        # happen, the cognatesets are globally sorted by the specified column
        # and within one group by size.
        if size_sort:
            cogsets.sort(
                key=lambda x: len(all_judgements[x[c_cogset_id]]),
                reverse=True,
            )
        if cogset_order is not None:
            cogsets.sort(key=lambda c: c[cogset_order])

        # iterate over all cogsets
        for cogset in cli.tq(
            cogsets,
            task="Wirting cognates and cognatesets to excel",
            total=len(cogsets),
        ):
            # possibly a cogset can appear without any judgment, if so ignore it
            if cogset[c_cogset_id] not in all_judgements:
                continue
            # write all forms of this cognateset to excel
            new_row_index = self.create_formcells_for_cogset(
                all_judgements[cogset[c_cogset_id]],
                ws,
                all_forms,
                row_index,
            )
            # write rows for cognatesets
            for row in range(row_index, new_row_index):
                for col, (db_name, header) in enumerate(self.header, 1):
                    # db_name is '' when add_central_concepts is activated
                    # and there is no concept column in cognateset table
                    # else read value from cognateset table
                    if header == "Central_Concept" and db_name == "":
                        # this is the concept associated to the first cognate in this cognateset
                        value = concept_id_by_form_id[
                            all_judgements[cogset[c_cogset_id]][0][c_cognate_form]
                        ]
                    else:
                        if db_name == "":
                            continue
                        column = self.dataset["CognatesetTable", db_name]
                        if column.separator is None:
                            value = cogset[db_name]
                        else:
                            value = column.separator.join(
                                [str(v) for v in cogset[db_name]]
                            )
                    cell = ws.cell(row=row, column=col, value=value)
                    # Transfer the cognateset comment to the first Excel cell.
                    if c_comment and col == 1 and cogset.get(c_comment):
                        cell.comment = op.comments.Comment(
                            re.sub(
                                f"-?{__package__}", "", cogset[c_comment] or ""
                            ).strip(),
                            "lexedata.exporter",
                        )

            row_index = new_row_index
        # write remaining forms to singleton congatesets if switch is activated
        if self.singleton:
            # remove all forms that appear in judgements
            for k in cli.tq(
                all_judgements,
                task="Write singleton cognatesets to excel",
                total=len(all_judgements),
            ):
                for judgement in all_judgements[k]:
                    form_id = judgement[c_cognate_form]
                    try:
                        del all_forms[form_id]
                    except KeyError:
                        continue
            # create for remaining forms singleton cognatesets and write to file
            try:
                c_cogset_concept = self.dataset[
                    "CognatesetTable", "parameterReference"
                ].name
            except KeyError:
                c_cogset_concept = None
            for i, form_id in enumerate(all_forms):
                # write form to file
                form = all_forms[form_id]
                self.create_formcell(
                    (form, dict()), ws, self.lan_dict[form[c_language]], row_index
                )
                # write singleton cognateset to excel
                for col, (db_name, header) in enumerate(self.header, 1):
                    if db_name == c_cogset_id:
                        value = f"X{i+1}_{form[c_language]}"
                    elif db_name == c_cogset_name:
                        value = concept_id_by_form_id[form_id]
                    elif db_name == c_cogset_concept:
                        value = concept_id_by_form_id[form_id]
                    elif header == "Status_Column" and status_update is not None:
                        value = status_update
                    else:
                        value = ""
                    ws.cell(row=row_index, column=col, value=value)
                row_index += 1
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
        cell_value = self.form_to_cell_value(judgement[0], judgement[1])
        form_cell = ws.cell(row=row, column=column, value=cell_value)
        c_id = self.dataset["FormTable", "id"].name
        try:
            c_comment = self.dataset["CognateTable", "comment"].name
        except KeyError:
            c_comment = None
        comment = judgement[1].get(c_comment, None)
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
            transcription = form["Form"]
        else:
            transcription = ""
            # TODO: use CLDF property instead of column name
            if not meta.get("Segment_Slice"):
                meta["Segment_Slice"] = ["0:{:d}".format(len(segments))]
            # What if segments overlap or cross? Overlap shouldn't happen, but
            # we don't check here. Crossing might happen, but this
            # serialization cannot reflect it, so we enforce order, expecting
            # that an error message here will be more useful than silently
            # messing with data.
            included_segments = set(
                parse_segment_slices(meta["Segment_Slice"], enforce_ordered=True)
            )

            included = False
            for i, s in enumerate(segments):
                if included and i not in included_segments:
                    transcription += " }" + s
                    included = False
                elif not included and i in included_segments:
                    transcription += "{ " + s
                    included = True
                elif i in included_segments:
                    transcription += " " + s
                else:
                    transcription += s
            if included:
                transcription += " }"

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
        try:
            c_segments = self.dataset["FormTable", "Segments"].name
            return form[c_segments]
        except KeyError:
            return None


if __name__ == "__main__":
    parser = cli.parser(description="Create an Excel cognate view from a CLDF dataset")
    parser.add_argument(
        "excel",
        type=Path,
        help="File path for the generated cognate excel file.",
    )
    parser.add_argument(
        "--size-sort",
        action="store_true",
        default=False,
        help="List the biggest cognatesets first (within a group, if another sort order is specified by --sort-cognatesets-by)",
    )
    parser.add_argument(
        "--sort-languages-by",
        help="The name of a column in the LanguageTable to sort languages by in the output",
    )
    parser.add_argument(
        "--sort-cognatesets-by",
        help="The name of a column in the CognatesetTable to sort cognates by in the output",
        default="id",
    )
    parser.add_argument(
        "--url-template",
        type=str,
        default="https://example.org/lexicon/{:}",
        help="A template string for URLs pointing to individual forms. For example, to"
        " point to lexibank, you would use https://lexibank.clld.org/values/{:}."
        " (default: https://example.org/lexicon/{:})",
    )
    parser.add_argument(
        "--add-singletons-with-status",
        default=None,
        metavar="MESSAGE",
        help="Include in the output all forms that don't belong to a cognateset. For each form, a singleton cognateset is created, and its status column (if there is one) is set to MESSAGE.",
    )
    parser.add_argument(
        "--add-singletons",
        action="store_const",
        const="automatic singleton",
        help="Short for `--add-singletons-with-status='automatic singleton'`",
        dest="add_singletons_with_status",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)
    E = ExcelWriter(
        pycldf.Wordlist.from_metadata(args.metadata),
        database_url=args.url_template,
        singleton_cognate=args.add_singletons_with_status is None,
    )
    try:
        cogset_order = E.dataset["CognatesetTable", args.sort_cognatesets_by].name
    except KeyError:
        cli.Exit.INVALID_COLUMN_NAME(
            f"No column '{args.sort_cognatesets_by}' in your CognatesetTable."
        )

    E.create_excel(
        args.excel,
        size_sort=args.size_sort,
        cogset_order=cogset_order,
        language_order=args.sort_languages_by,
        status_update=args.add_singletons_with_status,
    )
