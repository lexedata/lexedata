import typing as t

import pycldf

import lexedata.cli as cli


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
        description="Add Status_Column to specified tables of the dataset"
    )
    parser.add_argument(
        "table-names",
        type=str,
        nargs="*",
        default=[],
        help="Table names where to add Status_Column "
        "(default: FormTable, CognatesetTable, CognateTable, ParameterTable)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default=[],
        action="append",
        help="Table names to exclude (takes precedence over table-names)",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)
    # TODO: This should be made to work also for URLs, not just for names. Then
    # someone can have their custom tables, and run 'add_status_column *.csv
    # --exclude FormTable'
    if args.table_names:
        table_names = args.table_names
    else:
        table_names = [
            "FormTable",
            "CognatesetTable",
            "CognateTable",
            "ParameterTable",
        ]
    table_names = [name for name in table_names if name not in args.exclude_tables]
    logger.info("Tables to have a status column: {tables}".format(tables=table_names))
    dataset = pycldf.Dataset.from_metadata(args.metadata)
    status_column_to_table_list(dataset=dataset, tables=table_names)
