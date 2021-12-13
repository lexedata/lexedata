"""Starting with a forms.csv, add metadata for all columns we know about.
"""

from pathlib import Path

import pycldf
from csvw.dsv import iterrows
from csvw.metadata import Column, Datatype, TableGroup

from lexedata import cli

DEFAULT_NAME_COLUMNS = {
    column.name: column
    for column in (term.to_column() for term in pycldf.TERMS.values())
}

LEXEDATA_COLUMNS = {
    "Status": Column(
        datatype=Datatype(base="string"),
        default="",
        lang="eng",
        null=[""],
        name="Value",
        aboutUrl="...",
    ),
    "Orthographic": Column(
        datatype=Datatype(base="string"),
        default="",
        null=[""],
        name="Orthographic",
        aboutUrl="...",
    ),
    "Phonemic": Column(
        datatype=Datatype(base="string"),
        default="",
        null=[""],
        name="Phonemic",
        aboutUrl="...",
    ),
    "Phonetic": Column(
        datatype=Datatype(base="string"),
        default="",
        null=[""],
        name="Phonetic",
        aboutUrl="...",
    ),
    "variants": Column(
        datatype=Datatype(base="string", format=r"\s*(~|)\s*[/(<[].*[]/)>]\s*"),
        separator=",",
        default="",
        null=[""],
        name="variants",
    ),
    "Tags": Column(
        datatype=Datatype(base="string"),
        separator=",",
        default="",
        null=[""],
        name="Tags",
    ),
    "Loan": Column(
        datatype=Datatype(base="string"),
        default="",
        null=[""],
        name="Loan",
        aboutUrl="...",
    ),
}

LINGPY_COLUMNS = {
    "IPA": pycldf.TERMS["form"].to_column(),
    "DOCULECT": pycldf.TERMS["languageReference"].to_column(),
}

OTHER_KNOWN_COLUMNS = {
    "Form_according_to_Source": Column(
        datatype=Datatype(base="string"),
        default="",
        null=[""],
        name="Form_according_to_Source",
        required=True,
    ),
    "Page": Column(
        datatype=Datatype(base="string", format=r"\d+(-\d+)?"),
        separator=",",
        default="",
        null=["", "?"],
        name="Page",
    ),
    "Concept_ID": pycldf.TERMS["parameterReference"].to_column(),
}


def add_metadata(fname: Path, logger: cli.logging.Logger = cli.logger):
    if fname.name != "forms.csv":
        cli.Exit.CLI_ARGUMENT_ERROR(
            "A metadata-free Wordlist must be in a file called 'forms.csv'."
        )
    default_wordlist = TableGroup.from_file(
        pycldf.util.pkg_path("modules", "Wordlist-metadata.json")
    )
    default_wordlist._fname = fname.with_name("Wordlist-metadata.json")
    ds = pycldf.Wordlist(default_wordlist)

    # `from_data` checks that the reqired columns of the FormTable are present,
    # but it does not consolidate the columns further.

    colnames = next(iterrows(fname))

    understood_colnames = {
        c.name for c in ds[ds.primary_table].tableSchema.columns if c.name in colnames
    }
    more_columns = {
        c.propertyUrl.uri: c
        for c in ds[ds.primary_table].tableSchema.columns
        if c.name not in understood_colnames
    }
    logger.info(
        "CLDF freely understood the columns %s in your forms.csv.",
        sorted(understood_colnames),
    )

    # Consider the columns that were not understood.
    columns_without_metadata = set(colnames) - understood_colnames
    for column_name in columns_without_metadata:
        column: Column
        # Maybe they are known CLDF properties?
        if column_name in pycldf.terms.TERMS:
            column = pycldf.TERMS[column_name].to_column()
        # Maybe they are CLDF default column names?
        elif column_name in DEFAULT_NAME_COLUMNS:
            column = DEFAULT_NAME_COLUMNS[column_name]
        # Maybe they are columns that Lexedata knows to handle?
        elif column_name in LEXEDATA_COLUMNS:
            column = LEXEDATA_COLUMNS[column_name]
        # Maybe they are columns inherited from LingPy?
        elif column_name.upper() in LINGPY_COLUMNS:
            column = LINGPY_COLUMNS[column_name.upper()]
        # Maybe they are some name we have seen before?
        elif column_name in OTHER_KNOWN_COLUMNS:
            column = OTHER_KNOWN_COLUMNS[column_name]
        else:
            # TODO: Maybe they look like they have a specific type?
            ...
            # Otherwise, they are probably just text to be kept.
            column = Column(
                datatype=Datatype(base="string"),
                default="",
                null=[""],
                name=column_name,
            )
        column.name = column_name

        ds[ds.primary_table].tableSchema.columns.append(column)
        summary = column.propertyUrl or column.datatype
        logger.info(f"Column {column_name} seems to be a {summary} column.")
        if column.propertyUrl:
            to_be_replaced = more_columns.pop(column.propertyUrl.uri, None)
            if to_be_replaced is not None:
                ds[ds.primary_table].tableSchema.columns.remove(to_be_replaced)

    for column in more_columns.values():
        logger.info(f"Also added column {column.name}, as expected for a FormTable.")

    ds[ds.primary_table].tableSchema.columns.sort(
        key=lambda k: colnames.index(k.name) if k.name in colnames else 1e10
    )

    # TODO: Once lexedata is properly published, we can give a better URL.
    ds.properties["dc:contributor"] = [
        "https://github.com/Anaphory/lexedata/blob/master/src/lexedata/edit/add_metadata.py"
    ]
    return ds
