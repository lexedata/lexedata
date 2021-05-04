import sys
import typing as t
from pathlib import Path

import pycldf

from lexedata import util
from lexedata import types
from lexedata import cli

import xml.etree.ElementTree as ET

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


# Some type aliases, which should probably be moved elsewhere or made obsolete.
class Language_ID(str):
    pass


class Parameter_ID(str):
    pass


class Cognateset_ID(str):
    pass


def read_cldf_dataset(
    filename: Path,
    code_column: t.Optional[str] = None,
    logger: cli.logging.Logger = cli.logger,
) -> t.Mapping[
    types.Language_ID, t.Mapping[types.Parameter_ID, t.Set[types.Cognateset_ID]]
]:
    """Load a CLDF dataset.

    Load the file as `json` CLDF metadata description file, or as metadata-free
    dataset contained in a single csv file.

    The distinction is made depending on the file extension: `.json` files are
    loaded as metadata descriptions, all other files are matched against the
    CLDF module specifications. Directories are checked for the presence of
    any CLDF datasets in undefined order of the dataset types.

    If use_ids == False, the reader is free to choose language names or
    language glottocodes for the output if they are unique.

    Examples
    --------

    >>> _= open("forms.csv", "w").write("""...""")

    Parameters
    ----------
    fname : str or Path
        Path to a CLDF dataset

    Returns
    -------
    Data:

    """
    dataset = util.get_dataset(filename)

    # Make sure this is a kind of dataset we can handle
    if dataset.module not in ("Wordlist", "StructureDataset"):
        raise ValueError(
            "{:} does not know how to interpret CLDF {:} data.".format(
                __package__,
                dataset.module,
            )
        )

    # Build actual data dictionary, based on dataset type
    if dataset.module == "Wordlist":
        return read_wordlist(dataset, code_column, logger=logger)
    elif dataset.module == "StructureDataset":
        return read_structure_dataset(dataset, logger=logger)
    else:
        raise ValueError("Module {:} not supported".format(dataset.module))


def read_wordlist(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    code_column: t.Optional[str],
    logger: cli.logging.Logger = cli.logger,
) -> t.MutableMapping[types.Language_ID, t.MutableMapping[types.Parameter_ID, t.Set]]:
    col_map = dataset.column_names

    if code_column:
        # Just in case that column was specified by property URL. We
        # definitely want the name. In any case, this will also throw a
        # helpful KeyError when the column does not exist.
        cognatesets = util.cache_table(
            dataset,
            {"form": col_map.forms.id, "code": dataset["FormTable", code_column].name},
        )
        target = col_map.forms.id
    else:
        # We search for cognatesetReferences in the FormTable or a separate
        # CognateTable.

        # Try the FormTable first.
        code_column = col_map.forms.cognatesetReference

        if code_column:
            # This is not the CLDF way, warn the user.
            logger.warning(
                "Your dataset has a cognatesetReference in the FormTable. Consider running lexedata.enrich.explict_cognate_judgements to create an explicit cognate table, if this is your dataset."
            )
            cognatesets = util.cache_table(
                dataset, {"form": col_map.forms.id, "code": code_column}
            )
            target = col_map.forms.id
        else:
            # There was no cognatesetReference in the form table. If we
            # find them in CognateTable (I mean, they should be there!), we
            # store them keyed with formReference.
            if (
                col_map.cognates
                and col_map.cognates.cognatesetReference
                and col_map.cognates.formReference
            ):
                code_column = col_map.cognates.cognatesetReference
                form_reference = col_map.cognates.formReference
                (foreign_key,) = [
                    key
                    for key in dataset["CognateTable"].tableSchema.foreignKeys
                    if key.columnReference == [code_column]
                ]
                (target,) = foreign_key.reference.columnReference
                cognatesets = util.cache_table(
                    dataset,
                    {"form": form_reference, "code": code_column},
                    "CognateTable",
                )
            else:
                raise ValueError(
                    "Dataset {:} has no cognatesetReference column in its "
                    "primary table or in a separate cognate table. "
                    "Is this a metadata-free wordlist and you forgot to "
                    "specify code_column explicitly?".format(dataset.tableSchema._fname)
                )

    # Cognate sets have been loaded. Consolidate.
    cognates_by_form: t.MutableMapping[
        types.Form_ID, t.Set[types.Cognateset_ID]
    ] = t.DefaultDict(set)
    for judgement in cognatesets.values():
        cognates_by_form[judgement["form"]].add(judgement["code"])
    parameter_column = col_map.forms.parameterReference

    # If one form can have multiple concepts,
    if dataset["FormTable", parameter_column].separator:

        def all_parameters(parameter):
            return list(parameter)

    else:

        def all_parameters(parameter):
            return [parameter]

    data: t.MutableMapping[
        types.Language_ID, t.MutableMapping[types.Parameter_ID, t.Set]
    ] = t.DefaultDict(lambda: t.DefaultDict(set))
    for row in dataset["FormTable"].iterdicts():
        language = row[col_map.forms.languageReference]
        for parameter in all_parameters(row[parameter_column]):
            data[language][parameter] |= cognates_by_form[row[target]]
    return data


def read_structure_dataset(
    dataset: pycldf.Wordlist, logger: cli.logging.Logger = cli.logger
) -> t.MutableMapping[types.Language_ID, t.MutableMapping[types.Parameter_ID, t.Set]]:
    col_map = dataset.column_names
    data: t.MutableMapping[
        types.Language_ID, t.MutableMapping[types.Parameter_ID, t.Set]
    ] = t.DefaultDict(lambda: t.DefaultDict(set))
    code_column = col_map.values.codeReference or col_map.values.value
    for row in dataset["ValueTable"]:
        lang_id = row[col_map.values.languageReference]
        feature_id = row[col_map.values.parameterReference]
        if row[code_column]:
            data[lang_id][feature_id].add(row[code_column])
    return data


def root_meaning_code(
    dataset: t.Mapping[
        types.Language_ID, t.Mapping[types.Parameter_ID, t.Set[types.Cognateset_ID]]
    ],
    core_concepts: t.Optional[t.Set[types.Parameter_ID]] = None,
    ascertainment: t.Sequence[Literal["0", "1", "?"]] = ["0"],
) -> t.Tuple[
    t.Mapping[types.Language_ID, t.List[Literal["0", "1", "?"]]],
    t.Mapping[types.Parameter_ID, t.Mapping[types.Cognateset_ID, int]],
]:
    """Create a root-meaning coding from cognate codes in a dataset

    Take the cognate code information from a wordlist, i.e. a mapping of the
    form {Language ID: {Concept ID: {Cognateset ID}}}, and generate a binary
    alignment from it that lists for every meaning which roots are used to
    represent that meaning in each language.

    Return the aligment, and the list of slices belonging to each meaning.

    The default ascertainment is the a single absence ('0'): The configuration
    where a form is absent from all languages is never observed, but always
    possible, so we add this entry for the purposes of ascertainment
    correction.

    Examples
    ========

    >>> alignment, concepts = root_meaning_code({"Language": {"Meaning": {"Cognateset 1"}}})
    >>> alignment
    {'Language': ['0', '1']}


    >>> alignment, concepts = root_meaning_code(
    ...   {"l1": {"m1": {"c1"}},
    ...    "l2": {"m1": {"c2"}, "m2": {"c1", "c3"}}})
    >>> sorted(concepts)
    ['m1', 'm2']
    >>> sorted(concepts["m1"])
    ['c1', 'c2']
    >>> {language: sequence[concepts["m1"]["c1"]] for language, sequence in alignment.items()}
    {'l1': '1', 'l2': '0'}
    >>> {language: sequence[concepts["m2"]["c3"]] for language, sequence in alignment.items()}
    {'l1': '?', 'l2': '1'}
    >>> list(zip(*sorted(zip(*alignment.values()))))
    [('0', '0', '1', '?', '?'), ('0', '1', '0', '1', '1')]

    """
    roots: t.Dict[types.Parameter_ID, t.Set[types.Cognateset_ID]] = {}
    for language, lexicon in dataset.items():
        for concept, cognatesets in lexicon.items():
            if core_concepts is None or concept in core_concepts:
                roots.setdefault(concept, set()).update(cognatesets)

    blocks = {}
    sorted_roots: t.Dict[types.Parameter_ID, t.List[types.Cognateset_ID]] = {}
    c = len(ascertainment)
    for concept in sorted(roots, key=hash):
        possible_roots = sorted(roots[concept], key=hash)
        sorted_roots[concept] = possible_roots
        blocks[concept] = {root: r for r, root in enumerate(possible_roots, c)}
        c += len(possible_roots)

    alignment: t.Dict[types.Language_ID, t.List[Literal["0", "1", "?"]]] = {}
    for language, lexicon in dataset.items():
        alignment[language] = list(ascertainment)
        for concept, possible_roots in sorted_roots.items():
            entries = lexicon.get(concept)
            if entries is None:
                alignment[language].extend(["?" for _ in possible_roots])
            else:
                alignment[language].extend(
                    ["1" if k in entries else "0" for k in possible_roots]
                )
    return alignment, blocks


def root_presence_code(
    dataset: t.Mapping[
        types.Language_ID, t.Mapping[types.Parameter_ID, t.Set[types.Cognateset_ID]]
    ],
    important: t.Callable[
        [t.Set[types.Parameter_ID]], t.Set[types.Parameter_ID]
    ] = lambda x: x,
    ascertainment: t.Sequence[Literal["0", "1", "?"]] = ["0"],
    logger: cli.logging.Logger = cli.logger,
) -> t.Tuple[
    t.Mapping[types.Language_ID, t.List[Literal["0", "1", "?"]]],
    t.Mapping[types.Cognateset_ID, int],
]:
    """Create a root-presence/absence coding from cognate codes in a dataset

    Take the cognate code information from a wordlist, i.e. a mapping of the
    form {Language ID: {Concept ID: {Cognateset ID}}}, and generate a binary
    alignment from it that lists for every root whether it is present in that
    language or not. Return it, and the association between cognatesets and
    characters.

    >>> alignment, roots = root_presence_code({"Language": {"Meaning": {"Cognateset 1"}}})
    >>> alignment
    {'Language': ['0', '1']}
    >>> roots
    {'Cognateset 1': 1}

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

    >>> alignment, roots = root_presence_code(
    ...     {"l1": {"m1": {"c1"}},
    ...      "l2": {"m1": {"c2"}, "m2": {"c1", "c3"}}})
    >>> sorted(roots)
    ['c1', 'c2', 'c3']
    >>> sorted_roots = sorted(roots.items())
    >>> {language: [sequence[k[1]] for k in sorted_roots] for language, sequence in alignment.items()}
    {'l1': ['1', '0', '?'], 'l2': ['1', '1', '1']}
    >>> list(zip(*sorted(zip(*alignment.values()))))
    [('0', '0', '1', '?'), ('0', '1', '1', '1')]

    If only some concepts associated with the root in question are attested for
    the target language, the function `important` is called on the concepts
    associated with the root. The function returns a subset of the associated
    concepts. If any of those concepts are attested, the root is assumed to be
    absent.

    By default, all concepts are considered ‘important’, that is, the function
    `important` is the identity function.

    """
    associated_concepts: t.MutableMapping[
        types.Cognateset_ID, t.Set[types.Parameter_ID]
    ] = t.DefaultDict(set)
    all_roots: t.Set[types.Cognateset_ID] = set()
    language_roots: t.MutableMapping[
        types.Language_ID, t.Set[types.Cognateset_ID]
    ] = t.DefaultDict(set)
    for language, lexicon in dataset.items():
        for concept, cognatesets in lexicon.items():
            if not cognatesets:
                logger.warning(
                    f"The root presence coder script got a language ({language}) with an improper lexicon: Concept {concept} is marked as present in the language, but no cognate sets are associated with it."
                )
            for cognateset in cognatesets:
                associated_concepts[cognateset].add(concept)
                all_roots.add(cognateset)
                language_roots[language].add(cognateset)

    all_roots_sorted: t.Sequence[types.Cognateset_ID] = sorted(all_roots, key=hash)

    alignment = {}
    for language, lexicon in dataset.items():
        alignment[language] = list(ascertainment)
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

    return alignment, {
        root: r for r, root in enumerate(all_roots_sorted, len(ascertainment))
    }


def multistate_code(
    dataset: t.Mapping[
        types.Language_ID, t.Mapping[types.Parameter_ID, t.Set[types.Cognateset_ID]]
    ],
) -> t.Tuple[t.Mapping[types.Language_ID, t.Sequence[t.Set[int]]], t.Sequence[int]]:
    """Create a multistate root-meaning coding from cognate codes in a dataset

    Take the cognate code information from a wordlist, i.e. a mapping of the
    form {Language ID: {Concept ID: {Cognateset ID}}}, and generate a multistate
    alignment from it that lists for every meaning which roots are used to
    represent that meaning in each language.

    Also return the number of roots for each concept.

    Examples
    ========

    >>> alignment, lengths = multistate_code({"Language": {"Meaning": {"Cognateset 1"}}})
    >>> alignment =={'Language': [{0}]}
    True
    >>> lengths == [1]
    True


    >>> alignment, statecounts = multistate_code(
    ...     {"l1": {"m1": {"c1"}},
    ...      "l2": {"m1": {"c2"}, "m2": {"c1", "c3"}}})
    >>> alignment["l1"][1]
    set()
    >>> alignment["l2"][1] == {0, 1}
    True
    >>> statecounts
    [2, 2]

    """
    roots: t.Dict[types.Parameter_ID, t.Set[types.Cognateset_ID]] = t.DefaultDict(set)
    for language, lexicon in dataset.items():
        for concept, cognatesets in lexicon.items():
            roots[concept].update(cognatesets)
    sorted_roots: t.Mapping[types.Parameter_ID, t.Sequence[types.Cognateset_ID]] = {
        concept: sorted(cognatesets, key=hash)
        for concept, cognatesets in sorted(roots.items())
    }

    states: t.List[int] = [len(roots) for _, roots in sorted_roots.items()]

    alignment: t.MutableMapping[types.Language_ID, t.List[t.Set[int]]] = t.DefaultDict(
        list
    )
    for language, lexicon in dataset.items():
        for concept, possible_roots in sorted_roots.items():
            entries = lexicon.get(concept)
            alignment[language].append(set())
            if entries:
                for entry in entries:
                    state = possible_roots.index(entry)
                    alignment[language][-1].add(state)
    return alignment, states


def raw_binary_alignment(alignment):
    return ["".join(data) for language, data in alignment.items()]


def raw_multistate_alignment(alignment, long_sep: str = ","):
    max_code = max(
        c for seq in alignment.values() for character in seq for c in character
    )

    if max_code < 10:

        def encode(s: t.Set[int]):
            if not s:
                return "?"
            elif len(s) == 1:
                return str(s.pop())
            else:
                return "({})".format("".join(str(c) for c in s))

        separator = ""

    else:

        def encode(s: t.Set[int]):
            if not s:
                return "?"
            elif len(s) == 1:
                return str(s.pop())
            else:
                return "({})".format(",".join(str(c) for c in s))

        separator = long_sep

    return [
        separator.join([encode(c) for c in sequence])
        for language, sequence in alignment.items()
    ], max_code + 1


def format_nexus(
    languages, sequences, n_symbols, n_characters, datatype, partitions=None
):
    max_length = max([len(str(lang)) for lang in languages])

    sequences = [
        "{} {} {}".format(lang, " " * (max_length - len(str(lang))), seq)
        for lang, seq in zip(languages, sequences)
    ]

    if partitions:
        charsetstrings = [
            "CharSet {id}={indices};".format(
                id=id, indices=" ".join(str(k) for k in indices)
            )
            for id, indices in partitions.items()
        ]
        charsets = """Begin Sets;
  {:}
End;""".format(
            "\n  ".join(charsetstrings)
        )
    else:
        charsets = ""

    return """#NEXUS
Begin Taxa;
  Dimensions ntax={len_taxa:d};
  TaxLabels {taxa:s};
End;

Begin Characters;
  Dimensions NChar={len_alignment:d};
  Format Datatype={datatype} Missing=? Gap=- Symbols="{symbols:s}" {tokens:s};
  Matrix
    [The first column is constant zero, for programs with ascertainment correction]
    {sequences:s}
  ;
End;

{charsets}
""".format(
        len_taxa=len(languages),
        taxa=" ".join([str(language) for language in languages]),
        charsets=charsets,
        len_alignment=n_characters,
        datatype="Restriction" if datatype == "binary" else "Standard",
        symbols=" ".join(str(i) for i in range(n_symbols)),
        tokens="Tokens" if n_symbols >= 10 else "",
        sequences="\n    ".join(sequences),
    )


def fill_beast(data_object: ET.Element):
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

    taxa = ET.SubElement(data_object, "taxonset", id="taxa", spec="TaxonSet")
    for lang in alignment:
        ET.SubElement(taxa, "taxon", id=f"{lang:}", spec="Taxon")


if __name__ == "__main__":
    parser = cli.parser(
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
        "--language-identifiers",
        type=str,
        default=None,
        help="Use this column as language identifiers, instead of language IDs.",
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
    parser.add_argument("--stats-file", type=Path, help="A file to write statistics to")
    args = parser.parse_args()
    cli.setup_logging(args)

    # Step 1: Prepare the output file. This only matters if the output is beast.
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
    # Otherwise, it's just making the file accessible.
    elif args.output_file is None:
        args.output_file = sys.stdout
    else:
        args.output_file = args.output_file.open("w")

    # Step 2: Load the raw data.
    ds: t.Mapping[
        Language_ID, t.Mapping[Language_ID, t.Set[Language_ID]]
    ] = read_cldf_dataset(args.metadata, code_column=args.code_column)

    languages: t.Set[str]
    if args.languages_list:
        languages = {lg.strip() for lg in args.languages_list.open().read().split("\n")}
    else:
        languages = set(ds.keys())

    # Step 3: Filter the data.
    ds = {
        language: {k: v for k, v in sequence.items() if k not in args.exclude_concept}
        for language, sequence in ds.items()
        if (languages is None) or (language in languages)
    }

    n_symbols, datatype = 2, "binary"
    partitions = None

    # Step 3: Code the data
    alignment: t.Mapping[Language_ID, str]
    if args.coding == "rootpresence":
        binal, cogset_indices = root_presence_code(ds)
        n_characters = len(next(iter(binal.values())))
        alignment = {key: "".join(value) for key, value in binal.items()}
        sequences = raw_binary_alignment(alignment)
    elif args.coding == "rootmeaning":
        binal, concept_cogset_indices = root_meaning_code(ds)
        n_characters = len(next(iter(binal.values())))
        alignment = {key: "".join(value) for key, value in binal.items()}
        sequences = raw_binary_alignment(alignment)
        partitions = {
            concept: cogsets.values()
            for concept, cogsets in concept_cogset_indices.items()
        }
    elif args.coding == "multistate":
        multial, concept_indices = multistate_code(ds)
        n_characters = len(next(iter(multial.values())))
        sequences, n_symbols = raw_multistate_alignment(multial, long_sep=",")
        datatype = "multistate"
    else:
        raise ValueError("Coding schema {:} unknown.".format(args.coding))

    # Step 4: Format the data for output
    if args.format == "raw":
        max_length = max([len(str(lang)) for lang in ds])
        for language, sequence in zip(ds, sequences):
            print(
                language,
                " " * (max_length - len(language)),
                sequence,
                file=args.output_file,
            )

    elif args.format == "nexus":
        args.output_file.write(
            format_nexus(
                ds,
                sequences,
                n_symbols=n_symbols,
                n_characters=n_characters,
                datatype=datatype,
                partitions=partitions,
            )
        )

    elif args.format == "beast":
        et = fill_beast(data_object)
        et.write(args.output_file, encoding="unicode")

    # Step 5: Maybe print some statistics to file.
    if args.stats_file:
        countlects = len(ds)
        countconcepts = len(next(iter(ds.values())))
        with args.stats_file.open("w") as s:
            print(
                f"""
            \\newcommand{{\\countlects}}{{{countlects}}}
            \\newcommand{{\\countconcepts}}{{{countconcepts}}}
            \\newcommand{{\\ncharacters}}{{{n_characters}}}
            """,
                file=s,
            )
