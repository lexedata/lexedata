import enum
import sys
import typing as t
from pathlib import Path
from typing import Literal

import lxml.etree as ET
import pycldf

from lexedata import cli, types, util


# Some type aliases, which should probably be moved elsewhere or made obsolete.
class Language_ID(str):
    pass


class Parameter_ID(str):
    pass


class Cognateset_ID(str):
    pass


def read_cldf_dataset(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
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
    >>> import tempfile
    >>> dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    >>> target = dirname / "forms.csv"
    >>> _size = open(target, "w", encoding="utf-8").write('''
    ... ID,Language_ID,Parameter_ID,Form,Cognateset_ID
    ... '''.strip())
    >>> ds = pycldf.Wordlist.from_data(target)

    {'autaa': defaultdict(<class 'set'>, {'Woman': {'WOMAN1'}, 'Person': {'PERSON1'}})}
    TODO: FIXME THIS EXAMPLE IS INCOMPLETE

    Parameters
    ----------
    fname : str or Path
        Path to a CLDF dataset

    Returns
    -------
    Data:

    """
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
        form_table_form = col_map.forms.form
        form_table_column = col_map.forms.id
        cognatesets = util.cache_table(
            dataset,
            columns={
                "form": form_table_column,
                "transcription": form_table_form,
                "code": dataset["FormTable", code_column].name,
            },
            filter=lambda row: bool(row[col_map.forms.form]),
        )
    else:
        # We search for cognatesetReferences in the FormTable or a separate
        # CognateTable.

        # Try the FormTable first.
        code_column = col_map.forms.cognatesetReference

        if code_column:
            # This is not the CLDF way, warn the user.
            form_table_column = col_map.forms.id
            form_table_form = col_map.forms.form
            logger.warning(
                "Your dataset has a cognatesetReference in the FormTable. Consider running lexedata.edit.add_cognate_table to create an explicit cognate table."
            )
            cognatesets = util.cache_table(
                dataset,
                columns={
                    "form": form_table_column,
                    "transcription": form_table_form,
                    "code": code_column,
                },
            )
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
                    if key.columnReference == [form_reference]
                ]
                (form_table_column,) = foreign_key.reference.columnReference
                cognatesets = util.cache_table(
                    dataset,
                    "CognateTable",
                    {"form": form_reference, "code": code_column},
                )
            else:
                raise ValueError(
                    "Dataset has no cognatesetReference column in its "
                    "primary table or in a separate cognate table. "
                    "Is this a metadata-free wordlist and you forgot to "
                    "specify code_column explicitly?"
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
    ]
    if "LanguageTable" in dataset:
        (langref_target,) = [
            key
            for key in dataset["FormTable"].tableSchema.foreignKeys
            if key.columnReference == [dataset["FormTable", "languageReference"].name]
        ]
        ref_col = langref_target.reference.columnReference[0]
        data = {lang[ref_col]: t.DefaultDict(set) for lang in dataset["LanguageTable"]}
    else:
        data = t.DefaultDict(lambda: t.DefaultDict(set))
    for row in dataset["FormTable"].iterdicts():
        if not row[col_map.forms.form]:
            # Transcription is empty, should not be a form. Skip, but maybe
            # warn if it was in a cognateset.
            if cognates_by_form[row[form_table_column]]:
                logger.warning(
                    "Form %s was given as empty (i.e. the source noted that the form is unknown), but it was judged to be in cognateset %s. I will ignore that cognate judgement.",
                    row[col_map.forms.id],
                    cognates_by_form[row[form_table_column]],
                )
            continue

        language = row[col_map.forms.languageReference]
        if row[col_map.forms.form] == "-":
            if cognates_by_form[row[form_table_column]]:
                logger.warning(
                    "Form %s was given as '-' (i.e. “concept is not available in language %s”), but it was judged to be in cognateset %s. I will ignore that cognate judgement.",
                    row[col_map.forms.id],
                    language,
                    cognates_by_form[row[form_table_column]],
                )
                cognates_by_form[row[form_table_column]] = set()
            for parameter in all_parameters(row[parameter_column]):
                if data[language][parameter]:
                    logger.warning(
                        "Form %s claims concept %s is not available in language %s, but cognatesets %s are allocated to that concept in that language already.",
                        row[col_map.forms.id],
                        parameter,
                        row[col_map.forms.languageReference],
                        data[language][parameter],
                    )
        for parameter in all_parameters(row[parameter_column]):
            data[language][parameter] |= cognates_by_form[row[form_table_column]]
    return data


def read_structure_dataset(
    dataset: pycldf.StructureDataset, logger: cli.logging.Logger = cli.logger
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
    core_concepts: t.Set[types.Parameter_ID] = types.WorldSet(),
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
    for concept in sorted(roots):
        possible_roots = sorted(roots[concept])
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
                concept_sequence: t.List[Literal["0", "1", "?"]] = [
                    "1" if k in entries else "0" for k in possible_roots
                ]
                alignment[language].extend(concept_sequence)
    return alignment, blocks


class AbsenceHeuristic(enum.Enum):
    CENTRALCONCEPT = 0
    HALFPRIMARYCONCEPTS = 1


class CodingProcedure(enum.Enum):
    ROOTPRESENCE = 0
    ROOTMEANING = 1
    MULTISTATE = 2


# TODO: Maybe this would make sense tied closer to AbsenceHeuristic?
def apply_heuristics(
    dataset: types.Wordlist,
    heuristic: t.Optional[AbsenceHeuristic] = None,
    primary_concepts: t.Union[
        types.WorldSet[types.Parameter_ID], t.AbstractSet[types.Parameter_ID]
    ] = types.WorldSet(),
    logger: cli.logging.Logger = cli.logger,
) -> t.Mapping[types.Cognateset_ID, t.Set[types.Parameter_ID]]:
    """Compute the relevant concepts for cognatesets, depending on the heuristic.

    These concepts will be considered when deciding whether a root is deemed
    absent in a language.

    For the CentralConcept heuristic, the relevant concepts are the
    central concept of a cognateset, as given by the #parameterReference column
    of the CognatesetTable. A central concept not included in the
    primary_concepts is ignored with a warning.

    >>> ds = util.fs.new_wordlist()
    >>> cst = ds.add_component("CognatesetTable")
    >>> ds["CognatesetTable"].tableSchema.columns.append(
    ...     pycldf.dataset.Column(
    ...         name="Central_Concept",
    ...         propertyUrl="http://cldf.clld.org/v1.0/terms.rdf#parameterReference"))
    >>> ds.auto_constraints(cst)
    >>> ds.write(CognatesetTable=[
    ...     {"ID": "cognateset1", "Central_Concept": "concept1"}
    ... ])
    >>> apply_heuristics(ds, heuristic=AbsenceHeuristic.CENTRALCONCEPT) == {'cognateset1': {'concept1'}}
    True

    This extends to the case where a cognateset may have more than one central concept.

    >>> ds = util.fs.new_wordlist()
    >>> cst = ds.add_component("CognatesetTable")
    >>> ds["CognatesetTable"].tableSchema.columns.append(
    ...     pycldf.dataset.Column(
    ...         name="Central_Concepts",
    ...         propertyUrl="http://cldf.clld.org/v1.0/terms.rdf#parameterReference",
    ...         separator=","))
    >>> ds.auto_constraints(cst)
    >>> ds.write(CognatesetTable=[
    ...     {"ID": "cognateset1", "Central_Concepts": ["concept1", "concept2"]}
    ... ])
    >>> apply_heuristics(ds, heuristic=AbsenceHeuristic.CENTRALCONCEPT) == {
    ...     'cognateset1': {'concept1', 'concept2'}}
    True

    For the HalfPrimaryConcepts heurisitc, the relevant concepts are all
    primary concepts connected to a cognateset.

    >>> ds = util.fs.new_wordlist(
    ...     FormTable=[
    ...         {"ID": "f1", "Parameter_ID": "c1", "Language_ID": "l1", "Form": "x"},
    ...         {"ID": "f2", "Parameter_ID": "c2", "Language_ID": "l1", "Form": "x"}],
    ...     CognateTable=[
    ...         {"ID": "1", "Form_ID": "f1", "Cognateset_ID": "s1"},
    ...         {"ID": "2", "Form_ID": "f2", "Cognateset_ID": "s1"}])
    >>> apply_heuristics(ds, heuristic=AbsenceHeuristic.HALFPRIMARYCONCEPTS) == {
    ...     's1': {'c1', 'c2'}}
    True


    NOTE: This function cannot guarantee that every concept has at least one
    relevant concept, there may be cognatesets without! A cognateset with 0
    relevant concepts will always be included, because 0 is at least half of 0.

    """
    heuristic = (
        heuristic
        if heuristic is not None
        else (
            AbsenceHeuristic.CENTRALCONCEPT
            if ("CognatesetTable", "parameterReference") in dataset
            else AbsenceHeuristic.HALFPRIMARYCONCEPTS
        )
    )

    relevant_concepts: t.MutableMapping[
        types.Cognateset_ID, t.Set[types.Parameter_ID]
    ] = t.DefaultDict(set)

    if heuristic is AbsenceHeuristic.HALFPRIMARYCONCEPTS:
        c_f = dataset["CognateTable", "formReference"].name
        c_s = dataset["CognateTable", "cognatesetReference"].name
        concepts = util.cache_table(
            dataset,
            "FormTable",
            {"concepts": dataset["FormTable", "parameterReference"].name},
        )
        for j in dataset["CognateTable"]:
            form = concepts[j[c_f]]
            for concept in util.ensure_list(form["concepts"]):
                relevant_concepts[j[c_s]].add(concept)

    elif heuristic is AbsenceHeuristic.CENTRALCONCEPT:
        c_cognateset_concept = dataset["CognatesetTable", "parameterReference"].name
        c_id = dataset["CognatesetTable", "id"].name
        for c in dataset["CognatesetTable"]:
            for concept in util.ensure_list(c[c_cognateset_concept]):
                if concept not in primary_concepts:
                    logger.warning(
                        f"The central concept {concept} of cognateset {c[c_id]} was not part of your list of primary concepts to be included in the coding, so the cognateset will be ignored."
                    )
                else:
                    relevant_concepts[c[c_id]].add(concept)

    else:
        raise TypeError(
            f"Value of heuristic, {heuristic}, did not correspond to a known AbsenceHeuristic."
        )

    return relevant_concepts


def root_presence_code(
    dataset: t.Mapping[
        types.Language_ID, t.Mapping[types.Parameter_ID, t.Set[types.Cognateset_ID]]
    ],
    relevant_concepts: t.Mapping[types.Cognateset_ID, t.Iterable[types.Parameter_ID]],
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
    language or not. Return that, and the association between cognatesets and
    characters.

    >>> alignment, roots = root_presence_code(
    ...     {"Language": {"Meaning": {"Cognateset 1"}}},
    ...     relevant_concepts={"Cognateset 1": ["Meaning"]})
    >>> alignment
    {'Language': ['0', '1']}
    >>> roots
    {'Cognateset 1': 1}

    The first entry in each sequence is always '0': The configuration where a
    form is absent from all languages is never observed, but always possible,
    so we add this entry for the purposes of ascertainment correction.

    If a root is attested at all, in any concept, it is considered present.
    Because the word list is never a complete description of the language's
    lexicon, the function employs a heuristic to generate ‘absent’ states.

    If a root is unattested, and at least half of the relevant concepts
    associated with this root are attested, but each expressed by another root,
    the root is assumed to be absent in the target language. (If there is
    exactly one central concept, then that central concept being attested or
    unknown is a special case of this general rule.) Otherwise the
    presence/absence of the root is considered unknown.

    >>> alignment, roots = root_presence_code(
    ...     {"l1": {"m1": {"c1"}},
    ...      "l2": {"m1": {"c2"}, "m2": {"c1", "c3"}}},
    ...     relevant_concepts={"c1": ["m1"], "c2": ["m1"], "c3": ["m2"]})
    >>> sorted(roots)
    ['c1', 'c2', 'c3']
    >>> sorted_roots = sorted(roots.items())
    >>> {language: [sequence[k[1]] for k in sorted_roots] for language, sequence in alignment.items()}
    {'l1': ['1', '0', '?'], 'l2': ['1', '1', '1']}
    >>> list(zip(*sorted(zip(*alignment.values()))))
    [('0', '0', '1', '?'), ('0', '1', '1', '1')]

    """
    all_roots: t.Set[types.Cognateset_ID] = set(relevant_concepts)
    language_roots: t.MutableMapping[
        types.Language_ID, t.Set[types.Cognateset_ID]
    ] = t.DefaultDict(set)
    for language, lexicon in dataset.items():
        for concept, cognatesets in lexicon.items():
            if not cognatesets:
                logger.warning(
                    f"The root presence coder script got a language ({language}) with an improper lexicon: There is a form associated with Concept {concept}, but no cognate sets are associated with it."
                )
            for cognateset in cognatesets:
                language_roots[language].add(cognateset)

    all_roots_sorted: t.Sequence[types.Cognateset_ID] = sorted(all_roots)

    alignment = {}
    roots = {}
    for language, lexicon in dataset.items():
        alignment[language] = list(ascertainment)
        for root in all_roots_sorted:
            roots[root] = len(alignment[language])
            if root in language_roots[language]:
                alignment[language].append("1")
            else:
                n_concepts = 0
                n_filled_concepts = 0
                for concept in relevant_concepts[root]:
                    n_concepts += 1
                    if lexicon.get(concept):
                        n_filled_concepts += 1
                if 2 * n_filled_concepts >= n_concepts:
                    alignment[language].append("0")
                else:
                    alignment[language].append("?")

    return alignment, roots


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
        concept: sorted(cognatesets) for concept, cognatesets in sorted(roots.items())
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
                return "({})".format("".join(str(c) for c in sorted(s)))

        separator = ""

    else:

        def encode(s: t.Set[int]):
            if not s:
                return "?"
            elif len(s) == 1:
                return str(s.pop())
            else:
                return "({})".format(",".join(str(c) for c in sorted(s)))

        separator = long_sep

    return [
        separator.join([encode(c) for c in sequence])
        for language, sequence in alignment.items()
    ], max_code + 1


def format_nexus(
    languages: t.Iterable[str],
    sequences: t.Iterable[str],
    n_symbols: int,
    n_characters: int,
    datatype: str,
    partitions: t.Mapping[str, t.Iterable[int]] = None,
):
    """Format a Nexus output with the sequences.

    This function only formats and performs no further validity checks!

    >>> print(format_nexus(
    ...   ["l1", "l2"],
    ...   ["0010", "0111"],
    ...   2, 3,
    ...   "binary",
    ...   {"one": [1], "two": [2,3]}
    ... )) # doctest: +NORMALIZE_WHITESPACE
    #NEXUS
    Begin Taxa;
      Dimensions ntax=2;
      TaxLabels l1 l2;
    End;
    Begin Characters;
      Dimensions NChar=3;
      Format Datatype=Restriction Missing=? Gap=- Symbols="0 1" ;
      Matrix
        [The first column is constant zero, for programs with ascertainment correction]
        l1  0010
        l2  0111
      ;
    End;
    Begin Sets;
      CharSet one=1;
      CharSet two=2 3;
    End;

    """
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


def fill_beast(data_object: ET.Element, languages, sequences) -> None:
    """Add sequences to BEAST as Alignment object.

    >>> xml = ET.fromstring("<beast><data /></beast>")
    >>> fill_beast(xml.find(".//data"), ["L1", "L2"], ["0110", "0011"])
    >>> print(ET.tostring(xml).decode("utf-8"))
    <beast><data id="vocabulary" dataType="integer" spec="Alignment">
    <sequence id="language_data_vocabulary:L1" taxon="L1" value="0110"/>
    <sequence id="language_data_vocabulary:L2" taxon="L2" value="0011"/>
    <taxonset id="taxa" spec="TaxonSet"><plate var="language" range="{languages}"><taxon id="$(language)" spec="Taxon"/></plate></taxonset></data></beast>

    """
    # TODO: That doctest is a bit too harsh, it's not like line breaks are
    # forbidden. Think about which guarantees we want to give.
    data_object.clear()
    data_object.attrib["id"] = "vocabulary"
    data_object.attrib["dataType"] = "integer"
    data_object.attrib["spec"] = "Alignment"
    data_object.text = "\n"
    for language, sequence in zip(languages, sequences):
        seq = "".join(sequence)
        ET.SubElement(
            data_object,
            "sequence",
            id=f"language_data_vocabulary:{language:}",
            taxon=f"{language:}",
            value=f"{seq:}",
        ).tail = "\n"

    taxa = ET.SubElement(data_object, "taxonset", id="taxa", spec="TaxonSet")
    plate = ET.SubElement(taxa, "plate", var="language", range="{languages}")
    ET.SubElement(plate, "taxon", id="$(language)", spec="Taxon")


def compress_indices(indices: t.Set[int]) -> t.Iterator[slice]:
    """Turn groups of largely contiguous indices into slices.

    >>> list(compress_indices(set(range(10))))
    [slice(0, 10, None)]

    >>> list(compress_indices([1, 2, 5, 6, 7]))
    [slice(1, 3, None), slice(5, 8, None)]
    """
    if not indices:
        return
    minimum = min(indices)
    maximum = minimum
    while maximum in indices:
        indices.remove(maximum)
        maximum += 1
    yield slice(minimum, maximum)
    for sl in compress_indices(indices):
        yield sl


def add_partitions(data_object: ET.Element, partitions):
    previous_alignment = data_object
    for name, indices in partitions.items():
        indices_set = compress_indices(set(indices))
        indices_string = ",".join(
            "{:d}-{:d}".format(s.start + 1, s.stop) for s in indices_set
        )
        previous_alignment.addnext(
            data_object.makeelement(
                "data",
                {
                    "id": "concept:" + name,
                    "spec": "FilteredAlignment",
                    "filter": "1," + indices_string,
                    "data": "@" + data_object.attrib["id"],
                    "ascertained": "true",
                    "excludefrom": "0",
                    "excludeto": "1",
                },
            )
        )


def parser():
    """Construct the CLI argument parser for this script."""
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description="Export a CLDF dataset to a coded character matrix to be used as input for phylogenetic analyses.",
    )

    parser.add_argument(
        "--format",
        choices=("csv", "raw", "beast", "nexus"),
        default="raw",
        help="""Output format: `raw` for one language name per row, followed by spaces and
            the character state vector; `nexus` for a complete Nexus file; `beast`
            for the <data> tag to copy to a BEAST file; `csv` for a CSV
            with languages in rows and characters in columns. (default: raw)""",
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
        "--languages",
        action=cli.SetOrFromFile,
        help="Languages to include in the alignment.",
    )
    parser.add_argument(
        "--concepts",
        action=cli.SetOrFromFile,
        help="Concepts to be included or treated as primary concepts.",
    )
    parser.add_argument(
        "--cognatesets",
        action=cli.SetOrFromFile,
        help="Cognate sets to consider for the alignment.",
    )
    parser.add_argument(
        "--coding",
        action=cli.enum_from_lower(CodingProcedure),
        default="RootMeaning",
        help="""Coding method: In the `RootMeaning` coding method, every character
        describes the presence or absence of a particular root morpheme or
        cognate class in the word(s) for a given meaning; In the
        `RootPresence`, every character describes (up to the limitations of the
        data, which might not contain marginal forms) the presence or absence
        of a root (morpheme) in the language, independet of which meaning that
        root is attested in; And in the `Multistate` coding, each character
        describes, possibly including uniform ambiguities, the cognate class of
        a meaning. (default: RootMeaning)""",
    )
    parser.add_argument(
        "--absence-heuristic",
        action=cli.enum_from_lower(AbsenceHeuristic),
        help="""In case of --coding=rootpresence, which heuristic should be used for the
        coding of absences? The default depends on whether the dataset contains
        a #parameterReference column in its CognatesetTable: If there is one,
        or for --heuristic=CentralConcept, a root is considered absent
        when that concept (or at least half of them, if it is multi-valued) are
        attested with other roots. In the other case, or for
        --heuristic=HalfPrimaryConcepts, a root is considered absent when
        at least half the the concepts it is connected to are attested with
        other roots in the language.""",
    )
    parser.add_argument(
        "--stats-file",
        type=Path,
        help="Path to a TeX file that will be filled with LaTeX command definitions for some summary statistics. (default: Don't write a stats file)",
    )
    return parser


if __name__ == "__main__":
    args = parser().parse_args()
    logger = cli.setup_logging(args)
    # Step 1: Load the raw data.
    dataset = pycldf.Dataset.from_metadata(args.metadata)

    # Step 1: Load the raw data.
    ds: t.Mapping[Language_ID, t.Mapping[Parameter_ID, t.Set[Cognateset_ID]]] = {
        language: {k: v for k, v in sequence.items() if k in args.concepts}
        for language, sequence in read_cldf_dataset(dataset).items()
        if language in args.languages
    }

    logger.info(f"Imported languages {set(ds)}.")

    # Step 2: Code the data
    n_symbols, datatype = 2, "binary"
    partitions = None
    alignment: t.Mapping[Language_ID, str]
    if args.coding == CodingProcedure.ROOTPRESENCE:
        relevant_concepts = apply_heuristics(
            dataset, args.absence_heuristic, primary_concepts=args.concepts
        )
        binal, cognateset_indices = root_presence_code(
            ds, relevant_concepts=relevant_concepts, logger=logger
        )
        exclude = {
            index
            for cognateset, index in cognateset_indices.items()
            if cognateset not in args.cognatesets
        }
        n_characters = len(next(iter(binal.values())))
        alignment = {
            key: "".join([v for i, v in enumerate(value) if i not in exclude])
            for key, value in binal.items()
        }
        sequences = raw_binary_alignment(alignment)
    elif args.coding == CodingProcedure.ROOTMEANING:
        binal, concept_cognateset_indices = root_meaning_code(ds)
        n_characters = len(next(iter(binal.values())))
        exclude = {
            index
            for concept, cognateset_indices in concept_cognateset_indices.items()
            for cognateset, index in cognateset_indices.items()
            if cognateset not in args.cognatesets
        }
        alignment = {
            key: "".join([v for i, v in enumerate(value) if i not in exclude])
            for key, value in binal.items()
        }
        sequences = raw_binary_alignment(alignment)
        partitions = {
            concept: cognatesets.values()
            for concept, cognatesets in concept_cognateset_indices.items()
        }
    elif args.coding == CodingProcedure.MULTISTATE:
        multial, concept_indices = multistate_code(ds)
        n_characters = len(next(iter(multial.values())))
        sequences, n_symbols = raw_multistate_alignment(multial, long_sep=",")
        datatype = "multistate"
    else:
        raise ValueError("Coding schema {:} unknown.".format(args.coding))

    # Step 3: Format the data for output
    if args.format == "raw":
        if args.output_file is None:
            output_file = sys.stdout
        else:
            output_file = args.output_file.open("w", encoding="utf-8")

        max_length = max([len(str(lang)) for lang in ds])
        for language, sequence in zip(ds, sequences):
            print(
                language,
                " " * (max_length - len(language)),
                sequence,
                file=output_file,
            )

    elif args.format == "nexus":
        if args.output_file is None:
            output_file = sys.stdout
        else:
            output_file = args.output_file.open("w", encoding="utf-8")

        output_file.write(
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
        # Prepare the output file.
        xmlparser = ET.XMLParser(remove_blank_text=True, resolve_entities=False)
        if args.output_file is None:
            root = ET.fromstring(
                """<beast><data /></beast> """,
                parser=xmlparser,
            )

        elif args.output_file.exists():
            for line in args.output_file.open("rb"):
                xmlparser.feed(line)
            root = xmlparser.close()
        else:
            root = ET.fromstring(
                """<beast><data /></beast>""",
                parser=xmlparser,
            )
        et = root.getroottree()
        datas = list(root.iter("data"))
        data_object = datas[0]

        fill_beast(data_object, ds, sequences)
        if partitions:
            add_partitions(data_object, partitions)
            for language_plate in root.iterfind(".//plate[@range='{partitions}']"):
                language_plate.set("range", ",".join(partitions))
        for language_plate in root.iterfind(".//plate[@range='{languages}']"):
            language_plate.set("range", ",".join(ds))
        if args.output_file:
            et.write(
                args.output_file.open("wb"),
                pretty_print=True,
                xml_declaration=True,
                encoding=et.docinfo.encoding,
            )
        else:
            print(
                ET.tostring(
                    root,
                    pretty_print=True,
                    xml_declaration=True,
                ).decode("utf-8")
            )

    # Step 4: Maybe print some statistics to file.
    if args.stats_file:
        countlects = len(ds)
        countconcepts = len(next(iter(ds.values())))
        with args.stats_file.open("w", encoding="utf-8") as s:
            print(
                f"""
            \\newcommand{{\\countlects}}{{{countlects}}}
            \\newcommand{{\\countconcepts}}{{{countconcepts}}}
            \\newcommand{{\\ncharacters}}{{{n_characters}}}
            """,
                file=s,
            )
