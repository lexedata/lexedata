# -*- coding: utf-8 -*-
from pathlib import Path

import pycldf

from lexedata import cli


class ExcelWriter:
    """Class logic for Excel matrix export."""

    # TODO: Transfer code from cognates.py to here, think about how the two scripts interact.


if __name__ == "__main__":
    raise NotImplementedError(
        "This script is a stub, the core functionality is not implemented yet."
    )

    parser = cli.parser(description="Create an Excel matrix view from a CLDF dataset")
    parser.add_argument(
        "excel",
        type=Path,
        help="File path for the generated cognate excel file.",
    )
    parser.add_argument(
        "--concept-list",
        type=Path,
        help="Output only the concepts listed in this file",
    )
    parser.add_argument(
        "--sort-languages-by",
        help="The name of a column in the LanguageTable to sort languages by in the output",
    )
    parser.add_argument(
        "--url-template",
        type=str,
        default="https://example.org/lexicon/{:}",
        help="A template string for URLs pointing to individual forms. For example, to"
        " point to lexibank, you would use https://lexibank.clld.org/values/{:}."
        " (default: https://example.org/lexicon/{:})",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    if args.concept_list:
        if not args.concept_list.exists():
            logger.critical("Concept list file %s not found.", args.concept_list)
            cli.Exit.FILE_NOT_FOUND()
        raise NotImplementedError

    E = ExcelWriter(
        pycldf.Wordlist.from_metadata(args.metadata),
        database_url=args.url_template,
        # TODO: maybe remove the add_central_concepts argument from this function?
    )
    E.create_excel(
        args.excel,
        language_order=args.language_sort_column,
        concepts=args.concept_filter,
    )
