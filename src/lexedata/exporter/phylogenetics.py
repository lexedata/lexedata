import csv
import sys
import typing as t
import collections
from pathlib import Path
import chardet
import warnings

import pycldf.dataset

from csvw.dsv import UnicodeDictReader

def sanitise_name(name):
    """
    Take a name for a language or a feature which has come from somewhere like
    a CLDF dataset and make sure it does not contain any characters which
    will cause trouble for BEAST or postanalysis tools.
    """
    return name.replace(" ", "_").replace(",", "")


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


def read_cldf_dataset(filename, code_column=None, expect_multiple=True):
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
    data = collections.defaultdict(lambda: collections.defaultdict(set))

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
                    cognatesets = collections.defaultdict(list)
                    for row in dataset["CognateTable"]:
                        cognatesets[row[form_reference]].add(row[code_column])
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
                data[lang_id][feature_id].add(row[code_column])
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
            data[lang_id][feature_id].add(row[code_column] or '')
        return data, language_code_map


def build_lang_ids(dataset, col_map):
    if col_map.languages is None:
        # No language table so we can't do anything
        return {}, {}

    col_map = col_map.languages
    lang_ids = {}
    language_code_map = {}

    # First check for unique names and Glottocodes
    names = []
    gcs = []
    langs = []
    for row in dataset["LanguageTable"]:
        langs.append(row)
        names.append(row[col_map.name])
        if row[col_map.glottocode]:
            gcs.append(row[col_map.glottocode])

    unique_names = len(set(names)) == len(names)
    unique_gcs = len(set(gcs)) == len(gcs) == len(names)

    log.info('{0} are used as language identifiers'.format(
        'Names' if unique_names else ('Glottocodes' if unique_gcs else 'dataset-local IDs')))

    for row in langs:
        if unique_names:
            # Use names if they're unique, for human-friendliness
            lang_ids[row[col_map.id]] = sanitise_name(row[col_map.name])
        elif unique_gcs:
            # Otherwise, use glottocodes as at least they are meaningful
            lang_ids[row[col_map.id]] = row[col_map.glottocode]
        else:
            # As a last resort, use the IDs which are guaranteed to be unique
            lang_ids[row[col_map.id]] = row[col_map.id]
        if row[col_map.glottocode]:
            language_code_map[lang_ids[row[col_map.id]]] = row[col_map.glottocode]
    return lang_ids, language_code_map


def root_meaning_code(dataset: t.Dict[t.Hashable, t.Dict[t.Hashable, t.Set[t.Hashable]]]):
    roots: t.Dict[t.Hashable, t.set[t.Hashable]] = {}
    for language, lexicon in dataset.items():
        for concept, cognatesets in lexicon.items():
            roots.setdefault(concept, set()).update(cognatesets)
    alignment: t.Dict[t.Hashable, t.List[t.Literal["0", "1", "?"]]] = {}
    for language, lexicon in dataset.items():
        alignment[language] = ['0']
        for concept, possible_roots in sorted(roots.items()):
            entries = lexicon.get(concept)
            if entries is None:
                alignment[language].extend(["?" for _ in sorted(possible_roots)])
            else:
                alignment[language].extend(["1" if k in entries else "0"
                                            for k in sorted(possible_roots)])
    return alignment

def raw_alignment(alignment):
    l = max([len(str(l)) for l in alignment])
    for language, data in alignment.items():
        yield "{language:} {spacer:} {data:}".format(
            language=language,
            spacer=" "*(l - len(str(language))),
            data="".join(data))


if __name__ == "__main__":
    import argparse
    import xml.etree.ElementTree as ET

    parser = argparse.ArgumentParser(description="Export a CLDF dataset (or similar) to bioinformatics alignments")
    parser.add_argument("--format", choices=("csv", "raw", "beast", "nexus"),
                        default="raw",
                        help="Target format: `raw` for one language name per row, followed by spaces and the alignment vector; `nexus` for a complete Nexus file; `beast` for the <data> tag to copy to a BEAST file, and `csv` for a CSV with languages in rows and features in columns.")
    parser.add_argument("--metadata", help="Path to metadata file for dataset input",
                        default="forms.csv")
    parser.add_argument("--output-file", type=Path,
                        help="File to write output to. (If format=xml and output file exists, replace the first `data` tag in there.) Default: Write to stdout")
    parser.add_argument("--code-column",
                        help="Name of the code column for metadata-free wordlists")
    parser.add_argument("--exclude-concept", "-x",
                        action="append", default=[],
                        help="Exclude this concept (can be used multiple times)")
    parser.add_argument("--coding", choices=("rootmeaning", "rootpresence", "multistate"),
                        default="rootmeaning",
                        help="Binarization method: In the `rootmeaning` coding system, every character describes the presence or absence of a particular root morpheme or cognate class in the word(s) for a given meaning; In the `rootpresence`, every character describes (up to the limitations of the data, which might not contain marginal forms) the presence or absence of a root (morpheme) in the language, independet of which meaning that root is attested in; And in the `multistate` coding, each character describes, possibly including uniform ambiguities, the cognate class of a meaning.")
    args = parser.parse_args()

    if args.format == "beast":
        if args.output_file is None:
            root = ET.fromstring("<beast><data /></beast>")
        elif args.output_file.exists():
            et = ET.parse(args.output_file)
            root = et.getroot()
        else:
            root = ET.fromstring("<beast><data /></beast>")
        datas = list(root.iter("data"))
        data_object = datas[0]

    if args.output_file is None:
        args.output_file = sys.stdout
    else:
        args.output_file = args.output_file.open("w")

    ds, language_map = read_cldf_dataset(args.metadata, code_column=args.code_column, expect_multiple=True)
    ds = {
        language: {
            k: v
            for k, v in sequence.items()
            if k not in args.exclude_concept}
        for language, sequence in ds.items()
        if language not in ["p-alor1249", "p-east2519", "p-timo1261", "indo1316-lexi", "tetu1246", "tetu1245-suai"]
    }

    if args.coding == "rootpresence":
        alignment = root_presence_code(ds)
    elif args.coding == "rootmeaning":
        alignment = root_meaning_code(ds)
    elif args.coding == "multistate":
        raise NotImplementedError(
            "There are some conceptual problems, for the case of more than 9 different values for a slot, that have made us not implement multistate codes yet.")
        alignment = multistate_code(ds)
    else:
        raise ValueError("Coding schema {:} unknown.".format(args.coding))

    if args.format == "raw":
        print("\n".join(raw_alignment(alignment)),
              file=args.output_file)
    elif args.format == "nexus":
        print("""#NEXUS
Begin Taxa;
  Dimensions ntax={len_taxa:d};
  TaxLabels {taxa:s}
End;

Begin Data;
  Dimensions NChar={len_alignment:d};
  Format Datatype=Standard, Missing=?;
  Matrix
    [The first column is constant zero, for programs who need that kind of thing for ascertainment correction]
    {sequences:s}
  ;
End;
        """.format(
            len_taxa = len(alignment),
            taxa = " ".join([str(language) for language in alignment]),
            len_alignment = len(next(iter(alignment.values()))),
            sequences = "\n    ".join(raw_alignment(alignment))),
              file=args.output_file)
    elif args.format == "beast":
        data_object.clear()
        data_object.attrib = {
            "id": "vocabulary",
            "dataType": "integer",
            "spec": "Alignment"}
        data_object.text = "\n"
        for language, sequence in alignment.items():
            sequence = "".join(sequence)
            ET.SubElement(
                data_object,
                "sequence",
                id=f"language_data_vocabulary:{language:}",
                taxon=f"{language:}",
                value=f"{sequence:}").tail="\n"
        et.write(args.output_file, encoding="unicode")




