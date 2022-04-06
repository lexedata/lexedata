import typing as t
from pathlib import Path

import pycldf

import lexedata.cli as cli
from lexedata.util import normalize_table_name


def add_status_column_to_table(dataset: pycldf.Dataset, table_name: str) -> None:
    if "Status_Column" not in dataset[table_name].tableSchema.columndict.keys():
        dataset.add_columns(table_name, "Status_Column")
    else:
        cli.logger.info(f"Table {table_name} already contains a Status_Column.")


def status_column_to_table_list(
    dataset: pycldf.Dataset, tables: t.List[str]
) -> pycldf.Dataset:
    for table in tables:
        add_status_column_to_table(dataset, table)
    return dataset


if __name__ == "__main__":

    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description="Add Status_Column to specified tables of the dataset",
    )
    parser.add_argument(
        "tables",
        type=str,
        nargs="*",
        default=[],
        help="Table names and files to which to add Status_Column "
        "(default: FormTable, CognatesetTable, CognateTable, ParameterTable)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="*",
        default=[],
        help="Table names to exclude (takes precedence over table-names)",
        metavar="TABLE",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    dataset = pycldf.Dataset.from_metadata(args.metadata)

    # TODO: This should be made to work also for URLs, not just for names. Then
    # someone can have their custom tables, and run 'add_status_column *.csv
    # --exclude FormTable'
    if args.tables:
        table_names = [normalize_table_name(t, dataset, logger) for t in args.tables]
    else:
        table_names = [
            normalize_table_name(t, dataset, logger)
            for t in [
                "FormTable",
                "CognatesetTable",
                "CognateTable",
                "ParameterTable",
            ]
        ]
    tables = [
        name
        for name in table_names
        if name not in [normalize_table_name(t, dataset, logger) for t in args.exclude]
        if name
    ]
    logger.info("Tables to have a status column: {tables}".format(tables=tables))
    status_column_to_table_list(dataset=dataset, tables=tables)
