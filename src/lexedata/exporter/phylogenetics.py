import re
import sys
import typing as t
import collections
from pathlib import Path
import warnings

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from lexedata.util import get_dataset


def sanitise_name(name: str) -> str:
    """Clean a name for phylogenetics analyses.

    Take a name for a language or a feature which has come from somewhere like
    a CLDF dataset and make sure it does not contain any characters which will
    cause trouble for BEAST or postanalysis tools.

    >>> sanitise_name("Idempotent")
    'Idempotent'
    >>> sanitise_name("Name with Spaces")
    'Name_with_Spaces'
    >>> sanitise_name("Name\\tcontaining much\\nwhitespace")
    'Name_containing_much_whitespace'
    >>> sanitise_name("Name for this, or that")
    'Name_for_this_or_that'

    """
    return re.sub(r"\s", "_", name).replace(",", "")


def read_cldf_dataset(
    filename, code_column=None, use_ids=False
) -> t.Tuple[t.Mapping[str, t.Mapping[str, t.Set[str]]], t.Mapping[str, str]]:
    """Load a CLDF dataset.

    Load the file as `json` CLDF metadata description file, or as metadata-free
    dataset contained in a single csv file.

    The distinction is made depending on the file extension: `.json` files are
    loaded as metadata descriptions, all other files are matched against the
    CLDF module specifications. Directories are checked for the presence of
    any CLDF datasets in undefined order of the dataset types.

    If use_ids == False (the default), the reader is free to choose language
    names or language glottocodes for the output if they are unique. With
    use_ids=True you can force the reader to use the data set's language ids.

    Examples
    --------

    >>> data, mapping = read_cldf_dataset(
    ...   Path(__file__).parent /
    ...   "../../../test/data/cldf/minimal/cldf-metadata.json")
    Names are used as language identifiers
    >>> mapping
    {}
    >>> dict(data)
    {'Autaa': defaultdict(<class 'set'>, {'Woman': {'WOMAN1'}, 'Person': {'PERSON1'}})}

    This function also works with cross-semantic cognate codes. For example, in
    the Maweti-Guaraní example dataset, the Aché forms meaning “two” are
    cognate with other languages' forms meaning “three”:

    >>> data, mapping = read_cldf_dataset(
    ...   Path(__file__).parent /
    ...   "../../../test/data/cldf/smallmawetiguarani/cldf-metadata.json")
    Names are used as language identifiers
    >>> mapping
    {}
    >>> data["Aché"]["two"]
    {'two8'}

    Parameters
    ----------
    fname : str or Path
        Path to a CLDF dataset

    Returns
    -------
    Dataset

    """
    dataset = get_dataset(filename)
    data: t.DefaultDict[str, t.DefaultDict[str, t.Set]] = t.DefaultDict(
        lambda: t.DefaultDict(set)
    )

    # Make sure this is a kind of dataset BEASTling can handle
    if dataset.module not in ("Wordlist", "StructureDataset"):
        raise ValueError(
            "BEASTling does not know how to interpret CLDF {:} data.".format(
                dataset.module
            )
        )

    # Build dictionaries of nice IDs for languages and features
    col_map = dataset.column_names
    lang_ids, language_code_map = build_lang_ids(dataset, col_map, use_ids=use_ids)
    feature_ids = {}
    if col_map.parameters:
        for row in dataset["ParameterTable"]:
            feature_ids[row[col_map.parameters.id]] = sanitise_name(
                row[col_map.parameters.id]
            )

    # Build actual data dictionary, based on dataset type
    if dataset.module == "Wordlist":
        # We search for cognatesetReferences in the FormTable or a separate
        # CognateTable.
        cognate_column_in_form_table = True
        # If we find them in CognateTable, we store them keyed with formReference:
        if (
            not code_column
        ):  # If code_column is given explicitly, we don't have to search!
            code_column = col_map.forms.cognatesetReference
            if not code_column:
                if (
                    col_map.cognates
                    and col_map.cognates.cognatesetReference
                    and col_map.cognates.formReference
                ):
                    code_column = col_map.cognates.cognatesetReference
                    form_reference = col_map.cognates.formReference
                    cognatesets: t.Dict[
                        t.Hashable, t.Set[t.Hashable]
                    ] = collections.defaultdict(set)
                    for row in dataset["CognateTable"]:
                        cognatesets[row[form_reference]].add(row[code_column])
                else:
                    raise ValueError(
                        "Dataset {:} has no cognatesetReference column in its "
                        "primary table or in a separate cognate table. "
                        "Is this a metadata-free wordlist and you forgot to "
                        "specify code_column explicitly?".format(filename)
                    )
                cognate_column_in_form_table = False

        language_column = col_map.forms.languageReference
        parameter_column = col_map.forms.parameterReference
        if dataset["FormTable", parameter_column].separator:

            def all_parameters(parameter):
                return list(parameter)

        else:

            def all_parameters(parameter):
                return [parameter]

        warnings.filterwarnings(
            "ignore",
            '.*Unspecified column "Cognate_Set"',
            UserWarning,
            r"csvw\.metadata",
            0,
        )
        warnings.filterwarnings(
            "ignore",
            '.*Unspecified column "{:}"'.format(code_column),
            UserWarning,
            r"csvw\.metadata",
            0,
        )
        # We know how to deal with a 'Cognate_Set' column, even in a
        # metadata-free CSV file

        for row in dataset["FormTable"].iterdicts():
            lang_id = lang_ids.get(row[language_column], row[language_column])
            for parameter in all_parameters(row[parameter_column]):
                feature_id = feature_ids.get(parameter, parameter)
                if cognate_column_in_form_table:
                    data[lang_id][feature_id].add(row[code_column])
                else:
                    data[lang_id][feature_id] = cognatesets[row[col_map.forms.id]]
        return data, language_code_map

    elif dataset.module == "StructureDataset":
        code_column = col_map.values.codeReference or col_map.values.value
        for row in dataset["ValueTable"]:
            lang_id = lang_ids.get(
                row[col_map.values.languageReference],
                row[col_map.values.languageReference],
            )
            feature_id = feature_ids.get(
                row[col_map.values.parameterReference],
                row[col_map.values.parameterReference],
            )
            data[lang_id][feature_id].add(row[code_column] or "")
        return data, language_code_map

    else:
        raise ValueError("Module {:} not supported".format(dataset.module))


def build_lang_ids(dataset, col_map, use_ids=False):
    """Create a language ID translation table.

    In the early days of CLDF, language tables often contained numerical IDs.
    Those were really intransparent to the intermediate data users, so this
    function tries to use sensible IDs instead. These days, this function is
    probably obsolete and supported largely for legacy reasons. However, it is
    possible, in principle, to encounter language IDs with ‘strange’ characters
    in them, and for those tables, this infrastructure is still useful.

    """
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
        if row.get(col_map.glottocode):
            gcs.append(row[col_map.glottocode])

    unique_names = len(set(names)) == len(names)
    unique_gcs = len(set(gcs)) == len(gcs) == len(names)

    if not use_ids:
        # TODO: Use standard logging interface, this is an INFO.
        print(
            "{0} are used as language identifiers".format(
                "Names"
                if unique_names
                else ("Glottocodes" if unique_gcs else "dataset-local IDs")
            )
        )

    for row in langs:
        if use_ids:
            lang_ids[row[col_map.id]] = row[col_map.id]
        elif unique_names:
            # Use names if they're unique, for human-friendliness
            lang_ids[row[col_map.id]] = sanitise_name(row[col_map.name])
        elif unique_gcs:
            # Otherwise, use glottocodes as at least they are meaningful
            lang_ids[row[col_map.id]] = row[col_map.glottocode]
        else:
            # As a last resort, use the IDs which are guaranteed to be unique
            lang_ids[row[col_map.id]] = row[col_map.id]
        if row.get(col_map.glottocode):
            language_code_map[lang_ids[row[col_map.id]]] = row[col_map.glottocode]
    lang_ids = dict(sorted(lang_ids.items()))
    language_code_map = dict(sorted(language_code_map.items()))
    return lang_ids, language_code_map


def root_meaning_code(
    dataset: t.Dict[t.Hashable, t.Mapping[t.Hashable, t.Set[t.Hashable]]]
) -> t.Mapping[t.Hashable, t.List[Literal["0", "1", "?"]]]:
    """Create a root-meaning coding from cognate codes in a dataset

    Take the cognate code information from a wordlist, i.e. a mapping of the
    form {Language ID: {Concept ID: {Cognateset ID}}}, and generate a binary
    alignment from it that lists for every meaning which roots are used to
    represent that meaning in each language. The first entry in each sequence
    is always '0': The configuration where a form is absent from all languages
    is never observed, but always possible, so we add this entry for the
    purposes of ascertainment correction.

    >>> root_meaning_code({"Language": {"Meaning": {"Cognateset 1"}}})
    {'Language': ['0', '1']}
    >>> root_meaning_code({"l1": {"m1": {"c1"}},
    ...                    "l2": {"m1": {"c2"}, "m2": {"c1", "c3"}}})
    {'l1': ['0', '1', '0', '?', '?'], 'l2': ['0', '0', '1', '1', '1']}

    """
    roots: t.Dict[t.Hashable, t.Set[t.Hashable]] = {}
    for language, lexicon in dataset.items():
        for concept, cognatesets in lexicon.items():
            roots.setdefault(concept, set()).update(cognatesets)
    alignment: t.Dict[t.Hashable, t.List[Literal["0", "1", "?"]]] = {}
    for language, lexicon in dataset.items():
        alignment[language] = ["0"]
        for concept, possible_roots in sorted(roots.items()):
            entries = lexicon.get(concept)
            if entries is None:
                alignment[language].extend(["?" for _ in sorted(possible_roots)])
            else:
                alignment[language].extend(
                    ["1" if k in entries else "0" for k in sorted(possible_roots)]
                )
    return alignment


def root_presence_code(
    dataset: t.Dict[t.Hashable, t.Mapping[t.Hashable, t.Set[t.Hashable]]],
    important: t.Callable[[t.Set[t.Hashable]], t.Set[t.Hashable]] = lambda x: x,
) -> t.Mapping[t.Hashable, t.List[Literal["0", "1", "?"]]]:
    """Create a root-presence/absence coding from cognate codes in a dataset

    Take the cognate code information from a wordlist, i.e. a mapping of the
    form {Language ID: {Concept ID: {Cognateset ID}}}, and generate a binary
    alignment from it that lists for every root whether it is present in that
    language or not.

    >>> root_presence_code({"Language": {"Meaning": {"Cognateset 1"}}})
    {'Language': ['0', '1']}

    The first entry in each sequence is always '0': The configuration where a
    form is absent from all languages is never observed, but always possible,
    so we add this entry for the purposes of ascertainment correction.

    Because the word list is never a complete description of the language's
    lexicon, the function employs the following heuristic: If a root is
    attested at all, it is considered present. If a root is unattested, and
    none of the concepts associated with this root is attested, the data on the
    root's presence is considered missing. If all the concepts associated with
    the root are present, but expressed by other roots, the root is assumed to
    be absent in the target language.

    >>> root_presence_code({"l1": {"m1": {"c1"}},
    ...                     "l2": {"m1": {"c2"}, "m2": {"c1", "c3"}}})
    {'l1': ['0', '1', '0', '?'], 'l2': ['0', '1', '1', '1']}

    If only some concepts associated with the root in question are attested for
    the target language, the function `important` is called on the concepts
    associated with the root. The function returns a subset of the associated
    concepts. If any of those concepts are attested, the root is assumed to be
    absent.

    By default, all concepts are considered ‘important’, that is, the function
    `important` is the identity function.

    """
    associated_concepts: t.Dict[t.Hashable, t.Set[t.Hashable]] = {}
    all_roots: t.Set[t.Hashable] = set()
    language_roots: t.Dict[t.Hashable, t.Set[t.Hashable]] = {}
    for language, lexicon in dataset.items():
        language_roots[language] = set()
        for concept, cognatesets in lexicon.items():
            for cognateset in cognatesets:
                associated_concepts.setdefault(cognateset, set()).add(concept)
                all_roots.add(cognateset)
                language_roots[language].add(cognateset)

    all_roots_sorted = sorted(all_roots)

    alignment: t.Dict[t.Hashable, t.List[Literal["0", "1", "?"]]] = {}
    for language, lexicon in dataset.items():
        alignment[language] = ["0"]
        for root in all_roots_sorted:
            if root in language_roots[language]:
                alignment[language].append("1")
            else:
                for concept in important(associated_concepts[root]):
                    if lexicon.get(concept):
                        alignment[language].append("0")
                        break
                else:
                    alignment[language].append("?")

    return alignment


def multistate_code(
    dataset: t.Dict[t.Hashable, t.Dict[t.Hashable, t.Set[t.Hashable]]]
) -> t.Mapping[t.Hashable, t.List[t.Optional[int]]]:
    """Create a multistate root-meaning coding from cognate codes in a dataset

    Take the cognate code information from a wordlist, i.e. a mapping of the
    form {Language ID: {Concept ID: {Cognateset ID}}}, and generate a multistate
    alignment from it that lists for every meaning which roots are used to
    represent that meaning in each language.

    >>> multistate_code({"Language": {"Meaning": {"Cognateset 1"}}})
    {'Language': [0]}
    >>> multistate_code({"l1": {"m1": {"c1"}},
    ...                    "l2": {"m1": {"c2"}, "m2": {"c1", "c3"}}})
    {'l1': [0, None], 'l2': [1, 0]}

    """
    roots: t.Dict[t.Hashable, t.Set[t.Hashable]] = {}
    for language, lexicon in dataset.items():
        for concept, cognatesets in lexicon.items():
            roots.setdefault(concept, set()).update(cognatesets)
    alignment: t.Dict[t.Hashable, t.List[t.Optional[int]]] = {}
    for language, lexicon in dataset.items():
        alignment[language] = []
        for concept, possible_roots in sorted(roots.items()):
            entries = lexicon.get(concept)
            if entries is None:
                alignment[language].append(None)
            else:
                alignment[language].append(
                    # TODO: Bleagh, this is ugly, intransparent, error-prone,
                    # and wrong. I typed it only because it is wrong anyway and
                    # needs to be replaced ASAP.
                    max(
                        range(len(possible_roots)),
                        key=lambda i: sorted(possible_roots)[i] in entries,
                    )
                )
    return alignment


def raw_alignment(alignment):
    max_length = max([len(str(a)) for a in alignment])
    for language, data in alignment.items():
        yield "{language:} {spacer:} {data:}".format(
            language=language,
            spacer=" " * (max_length - len(str(language))),
            data="".join(data),
        )


if __name__ == "__main__":
    import argparse
    import xml.etree.ElementTree as ET

    parser = argparse.ArgumentParser(
        description="Export a CLDF dataset (or similar) to bioinformatics alignments"
    )
    parser.add_argument(
        "--format",
        choices=("csv", "raw", "beast", "nexus"),
        default="raw",
        help="""Target format: `raw` for one language name per row, followed by spaces and
            the alignment vector; `nexus` for a complete Nexus file; `beast`
            for the <data> tag to copy to a BEAST file, and `csv` for a CSV
            with languages in rows and features in columns.""",
    )
    parser.add_argument(
        "-b",
        action="store_const",
        const="beast",
        dest="format",
        help="""Short form of --format=beast""",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=Path,
        help="""File to write output to. (If format=beast and output file exists, replace the
            first `data` tag in there.) (default: Write to stdout)""",
    )
    parser.add_argument(
        "--code-column",
        type=str,
        help="Name of the code column for metadata-free wordlists",
    )
    parser.add_argument(
        "--languages-list",
        default=None,
        type=Path,
        help="File to load a list of languages from",
    )
    parser.add_argument(
        "--use-ids",
        action="store_true",
        default=False,
        help="Use dataset's language IDs, instead of guessing whether names or glottocodes might be better.",
    )
    parser.add_argument(
        "--exclude-concept",
        "-x",
        action="append",
        default=[],
        help="Exclude this concept (can be used multiple times)",
    )
    parser.add_argument(
        "--coding",
        choices=("rootmeaning", "rootpresence", "multistate"),
        default="rootmeaning",
        help="""Binarization method: In the `rootmeaning` coding system, every character
            describes the presence or absence of a particular root morpheme or
            cognate class in the word(s) for a given meaning; In the
            `rootpresence`, every character describes (up to the limitations of
            the data, which might not contain marginal forms) the presence or
            absence of a root (morpheme) in the language, independet of which
            meaning that root is attested in; And in the `multistate` coding,
            each character describes, possibly including uniform ambiguities,
            the cognate class of a meaning.""",
    )
    parser.add_argument("--stats-file", type=Path, help="A file to write stats to")
    args = parser.parse_args()

    if args.format == "beast":
        if args.output_file is None:
            root = ET.fromstring("<beast><data /></beast>")
            et = ET.ElementTree(root)
        elif args.output_file.exists():
            et = ET.parse(args.output_file)
            root = et.getroot()
        else:
            root = ET.fromstring("<beast><data /></beast>")
            et = ET.ElementTree(root)
        datas = list(root.iter("data"))
        data_object = datas[0]

    if args.output_file is None:
        args.output_file = sys.stdout
    else:
        args.output_file = args.output_file.open("w")

    languages: t.Optional[t.Set[str]]
    ds, language_map = read_cldf_dataset(
        args.metadata, code_column=args.code_column, use_ids=args.use_ids
    )
    if args.languages_list:
        languages = {lg.strip() for lg in args.languages_list.open().read().split("\n")}
    elif language_map:
        languages = set(language_map)
    else:
        languages = None

    ds = {
        language: {k: v for k, v in sequence.items() if k not in args.exclude_concept}
        for language, sequence in ds.items()
        if (languages is None) or (language in languages)
    }

    if args.coding == "rootpresence":
        alignment = root_presence_code(ds)
    elif args.coding == "rootmeaning":
        alignment = root_meaning_code(ds)
    elif args.coding == "multistate":
        raise NotImplementedError(
            """There are some conceptual problems, for the case of more than 9 different
                values for a slot, that have made us not implement multistate
                codes yet."""
        )
        alignment = multistate_code(ds)
    else:
        raise ValueError("Coding schema {:} unknown.".format(args.coding))

    if args.format == "raw":
        print("\n".join(raw_alignment(alignment)), file=args.output_file)
    elif args.format == "nexus":
        print(
            """#NEXUS
Begin Taxa;
  Dimensions ntax={len_taxa:d};
  TaxLabels {taxa:s}
End;

Begin Data;
  Dimensions NChar={len_alignment:d};
  Format Datatype=Standard, Missing=?;
  Matrix
    [The first column is constant zero, for programs with ascertainment correction]
    {sequences:s}
  ;
End;
        """.format(
                len_taxa=len(alignment),
                taxa=" ".join([str(language) for language in alignment]),
                len_alignment=len(next(iter(alignment.values()))),
                sequences="\n    ".join(raw_alignment(alignment)),
            ),
            file=args.output_file,
        )
    elif args.format == "beast":
        data_object.clear()
        data_object.attrib = {
            "id": "vocabulary",
            "dataType": "integer",
            "spec": "Alignment",
        }
        data_object.text = "\n"
        for language, sequence in alignment.items():
            seq = "".join(sequence)
            ET.SubElement(
                data_object,
                "sequence",
                id=f"language_data_vocabulary:{language:}",
                taxon=f"{language:}",
                value=f"{seq:}",
            ).tail = "\n"
        et.write(args.output_file, encoding="unicode")

    if args.stats_file:
        countlects = len(ds)
        countconcepts = len(next(iter(ds.values())))
        with args.stats_file.open("w") as s:
            print(
                f"""
            \\newcommand{{\\countlects}}{{{countlects}}}
            \\newcommand{{\\countconcepts}}{{{countconcepts}}}
            """,
                file=s,
            )
