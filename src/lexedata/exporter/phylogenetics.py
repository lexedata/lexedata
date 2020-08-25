import csv
import sys
import typing
import collections
from pathlib import Path
import chardet
import warnings

import pycldf.dataset
from pathlib import Path

from csvw.dsv import UnicodeDictReader


def sanitise_name(name):
    """
    Take a name for a language or a feature which has come from somewhere like
    a CLDF dataset and make sure it does not contain any characters which
    will cause trouble for BEAST or postanalysis tools.
    """
    return name.replace(" ", "_")


def load_cldf_data(reader, value_column, filename, expect_multiple=False):
    value_column = value_column or "Value"
    if "Feature_ID" in reader.fieldnames:
        feature_column = "Feature_ID"
    elif "Parameter_ID" in reader.fieldnames:
        feature_column = "Parameter_ID"
    else:
        raise ValueError("Could not find Feature_ID or Parameter_ID column, is %s a valid CLDF file?" % filename)
    data = collections.defaultdict(lambda: collections.defaultdict(lambda: "?"))
    for row in reader:
        lang = row["Language_ID"]
        if lang not in data:
            if expect_multiple:
                data[lang] = collections.defaultdict(lambda: [])
            else:
                data[lang] = collections.defaultdict(lambda: "?")
        if expect_multiple:
            data[lang][row[feature_column]].append(row[value_column])
        else:
            data[lang][row[feature_column]] = row[value_column]
    return data


def iterlocations(filename):
    with UnicodeDictReader(filename, dialect=sniff(filename, default_dialect=None)) as reader:
        # Identify fieldnames
        fieldnames = [(n.lower(), n) for n in reader.fieldnames]
        fieldmap = {}

        for field, aliases in [
            ('language identifier', _language_column_names),
            ('latitude', ("latitude", "lat")),
            ('longitude', ("longitude", "lon", "long")),
        ]:
            for lname, fieldname in fieldnames:
                if lname in aliases:
                    fieldmap[field] = fieldname
                    break
            else:
                raise ValueError(
                    "Could not find a {0} column in location data file {1}".format(field, filename))

        for row in reader:
            (lat, lon) = row[fieldmap['latitude']], row[fieldmap['longitude']]
            try:
                lat = float(lat) if lat != "?" else lat
                lon = float(lon) if lon != "?" else lon
            except ValueError:
                lat, lon = "?", "?"
            yield (row[fieldmap['language identifier']].strip(), (lat, lon))


def get_dataset(fname):
    """Load a CLDF dataset.

    Load the file as `json` CLDF metadata description file, or as metadata-free
    dataset contained in a single csv file.

    The distinction is made depending on the file extension: `.json` files are
    loaded as metadata descriptions, all other files are matched against the
    CLDF module specifications. Directories are checked for the presence of
    any CLDF datasets in undefined order of the dataset types.

    Parameters
    ----------
    fname : str or Path
        Path to a CLDF dataset

    Returns
    -------
    Dataset
    """
    fname = Path(fname)
    if not fname.exists():
        raise FileNotFoundError('{:} does not exist'.format(fname))
    if fname.suffix == '.json':
        return pycldf.dataset.Dataset.from_metadata(fname)
    return pycldf.dataset.Dataset.from_data(fname)


# TODO: Change the behaviour to always expect multiple.
def read_cldf_dataset(filename, code_column=None, expect_multiple=False):
    """Load a CLDF dataset.

    Load the file as `json` CLDF metadata description file, or as metadata-free
    dataset contained in a single csv file.

    The distinction is made depending on the file extension: `.json` files are
    loaded as metadata descriptions, all other files are matched against the
    CLDF module specifications. Directories are checked for the presence of
    any CLDF datasets in undefined order of the dataset types.

    Parameters
    ----------
    fname : str or Path
        Path to a CLDF dataset

    Returns
    -------
    Dataset
    """
    dataset = get_dataset(filename)
    if expect_multiple:
        data = collections.defaultdict(lambda: collections.defaultdict(lambda: []))
    else:
        data = collections.defaultdict(lambda: collections.defaultdict(lambda: "?"))

    # Make sure this is a kind of dataset BEASTling can handle
    if dataset.module not in ("Wordlist", "StructureDataset"):
        raise ValueError("BEASTling does not know how to interpret CLDF {:} data.".format(
            dataset.module))

    # Build dictionaries of nice IDs for languages and features
    col_map = dataset.column_names
    lang_ids, language_code_map = build_lang_ids(dataset, col_map)
    feature_ids = {}
    if col_map.parameters:
        for row in dataset["ParameterTable"]:
            feature_ids[row[col_map.parameters.id]] = sanitise_name(row[col_map.parameters.name])

    # Build actual data dictionary, based on dataset type
    if dataset.module == "Wordlist":
        # We search for cognatesetReferences in the FormTable or a separate CognateTable.
        cognate_column_in_form_table = True
        # If we find them in CognateTable, we store them keyed with formReference:
        if not code_column:  # If code_column is given explicitly, we don't have to search!
            code_column = col_map.forms.cognatesetReference
            if not code_column:
                if (col_map.cognates and
                    col_map.cognates.cognatesetReference and
                    col_map.cognates.formReference):
                    code_column = col_map.cognates.cognatesetReference
                    form_reference = col_map.cognates.formReference
                    if expect_multiple:
                        cognatesets = collections.defaultdict(list)
                        for row in dataset["CognateTable"]:
                            cognatesets[row[form_reference]].append(row[code_column])
                    else:
                        cognatesets = collections.defaultdict(lambda: "?")
                        for row in dataset["CognateTable"]:
                            cognatesets[row[form_reference]] = row[code_column]
                else:
                    raise ValueError(
                        "Dataset {:} has no cognatesetReference column in its "
                        "primary table or in a separate cognate table. "
                        "Is this a metadata-free wordlist and you forgot to "
                        "specify code_column explicitly?".format(filename))
                form_column = dataset["FormTable", "id"].name
                cognate_column_in_form_table = False

        language_column = col_map.forms.languageReference
        parameter_column = col_map.forms.parameterReference

        warnings.filterwarnings(
            "ignore", '.*Unspecified column "Cognate_Set"', UserWarning, "csvw\.metadata", 0)
        warnings.filterwarnings(
            "ignore", '.*Unspecified column "{:}"'.format(code_column), UserWarning, "csvw\.metadata", 0)
        # We know how to deal with a 'Cognate_Set' column, even in a metadata-free CSV file

        for row in dataset["FormTable"].iterdicts():
            lang_id = lang_ids.get(row[language_column], row[language_column])
            feature_id = feature_ids.get(row[parameter_column], row[parameter_column])
            if cognate_column_in_form_table:
                if expect_multiple:
                    data[lang_id][feature_id].append(row[code_column])
                else:
                    data[lang_id][feature_id] = row[code_column]
            else:
                data[lang_id][feature_id] = cognatesets[row[col_map.forms.id]]
        return data, language_code_map

    if dataset.module == "StructureDataset":
        code_column = col_map.values.codeReference or col_map.values.value
        for row in dataset["ValueTable"]:
            lang_id = lang_ids.get(
                row[col_map.values.languageReference], row[col_map.values.languageReference])
            feature_id = feature_ids.get(
                row[col_map.values.parameterReference], row[col_map.values.parameterReference])
            if expect_multiple:
                data[lang_id][feature_id].append(row[code_column] or '')
            else:
                data[lang_id][feature_id] = row[code_column] or ''
        return data, language_code_map
