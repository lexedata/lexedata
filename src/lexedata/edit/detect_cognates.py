"""Similarity code tentative cognates in a word list and align them"""

import csv
import hashlib
import itertools
import typing as t
from pathlib import Path

import lexedata.cli as cli
import lexedata.types as types
import lingpy
import lingpy.compare.partial
import pycldf
import pyclts
import segments
from lexedata.edit.add_segments import bipa

# TODO maybe the CLTS logic from here and there belongs in util?

tokenizer = segments.Tokenizer()


def sha1(path):
    return hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12]


def _charstring(id_, char="X", cls="-"):
    return "{0}.{1}.{2}".format(id_, char, cls)


class SimpleScoreDict(dict):
    def __missing__(self, key):
        k1, k2 = key
        if k1 == k2:
            return 0.0
        else:
            return -1.0


def clean_segments(segment_string: t.List[str]) -> t.Iterable[pyclts.models.Symbol]:
    """Reduce the row's segments to not contain empty morphemes.

    This function removes all unknown sound segments (/0/) from the segments
    string it is passed, and removes empty morphemes by collapsing subsequent
    morpheme boundary markers (_#◦+→←) into one, normalizing the phonetics in
    the process.

    >>> segments = "t w o _ m o r ph e m e s".split()
    >>> c = clean_segments(segments)
    >>> [str(s) for s in c]
    ['t', 'w', 'o', '_', 'm', 'o', 'r', 'pʰ', 'e', 'm', 'e', 's']

    >>> segments = "+ _ t a + 0 + a t".split()
    >>> c = clean_segments(segments)
    >>> [str(s) for s in c]
    ['t', 'a', '+', 'a', 't']

    """
    segments = [bipa[x] for x in segment_string]
    segments.insert(0, bipa["#"])
    segments.append(bipa["#"])
    for s in range(len(segments) - 1, 0, -1):
        if not pyclts.models.is_valid_sound(segments[s - 1], bipa):
            if isinstance(segments[s - 1], pyclts.models.Marker) and isinstance(
                segments[s], pyclts.models.Marker
            ):
                del segments[s - 1]
            if isinstance(segments[s - 1], pyclts.models.UnknownSound):
                del segments[s - 1]
            continue
    return segments[1:-1]


def get_slices(tokens: t.List[str], include_empty=False) -> t.Iterator[slice]:
    """Return slices for all morphemes in the token string

    This function computes the morpheme slices in an annotated token set.
    Empty morphemes are not yielded, unless include_empty is set to True.

    >>> list(get_slices("t w o _ m o r ph e m e s".split()))
    [slice(0, 3, None), slice(4, 12, None)]

    >>> list(get_slices("+ _ t a + 0 + a t".split()))
    [slice(2, 4, None), slice(5, 6, None), slice(7, 9, None)]

    """
    start = 0
    i = -1
    for i, s in enumerate(tokens):
        if s in {"_", "#", "◦", "+", "→", "←"}:
            if i > start or include_empty:
                yield slice(start, i)
            start = i + 1
    i += 1
    if i > start or include_empty:
        yield slice(start, i)


def filter_function_factory(
    dataset: types.Wordlist,
) -> t.Callable[[t.Dict[str, t.Any]], bool]:
    def filter(row: t.Dict[str, t.Any]) -> bool:
        row["tokens"] = [
            str(x)
            for x in clean_segments(row[dataset.column_names.forms.segments.lower()])
        ]
        row["tokens"] = ["+" if x == "_" else x for x in row["tokens"]]
        # TODO: Find the official LingPy way to consider word boundaries to
        # also be morpheme boundaries – just adding them in
        # `partial_cluster(sep=...+'_')` did not work, and why isn't it the
        # default anyway?
        row["doculect"] = row[dataset.column_names.forms.languageReference.lower()]
        row["concept"] = row[dataset.column_names.forms.parameterReference.lower()]
        return row["segments"] and row["concept"]

    return filter


alignment_functions = {
    "global": lingpy.algorithm.calign.globalign,
    "local": lingpy.algorithm.calign.localign,
    "overlap": lingpy.algorithm.calign.semi_globalign,
    "dialign": lambda seqA, seqB, gopA, gopB, proA, proB, M, N, scale, factor, scorer: lingpy.algorithm.calign.dialign(
        seqA, seqB, proA, proB, M, N, scale, factor, scorer
    ),
}


def compute_one_matrix(
    tokens_by_index: t.Mapping[types.Form_ID, t.List[str]],
    align_function: t.Callable[[types.Form_ID, types.Form_ID, slice, slice], float],
) -> t.Tuple[
    t.Mapping[types.Form_ID, t.List[t.Tuple[slice, int]]], t.List[t.List[float]]
]:
    """Compute the distance matrix for pairwise alignment of related morphemes.

    Align all pairs of morphemes (presumably each of them part of a form
    associated to one common concept), while assuming there is no
    reduplication, so one morpheme in one form can be cognate (and thus have
    small relative edit distance) to at most one morpheme in another form.

    Return the identifiers of the morphemes, and the corresponding distance
    matrix.

    The align_function is a function that calculates the alignment score for
    two slices of token strings, such as

    >>> identity_scorer = SimpleScoreDict()
    >>> def align(f1, f2): return alignment_functions["global"](
    ...   f1, f2,
    ...   [-1 for _ in f1], [-1 for _ in f2],
    ...   ['X' for _ in f1], ['X' for _ in f2],
    ...   len(f1), len(f2),
    ...   scale = 0.5,
    ...   factor = 0.0,
    ...   scorer = identity_scorer
    ...   )[2] * 2 / (len(f2) + len(f1))
    >>> def slice_align(f1, f2, s1, s2): return align(data[f1][s1], data[f2][s2])

    In the simplest case, this is just a pairwise alignment, with optimum at 0.

    >>> data = {"f1": "form", "f2": "form"}
    >>> compute_one_matrix(data, slice_align)
    ({'f1': [(slice(0, 4, None), 0)], 'f2': [(slice(0, 4, None), 1)]}, [[0.0, 0.0], [0.0, 0.0]])

    This goes up with partial matches.

    >>> data = {"f1": "form", "f3": "fowl"}
    >>> compute_one_matrix(data, slice_align)
    ({'f1': [(slice(0, 4, None), 0)], 'f3': [(slice(0, 4, None), 1)]}, [[0.0, -0.5], [-0.5, 0.0]])

    If the forms are completely different, the matrix entries are negative values.

    >>> data = {"f1": "form", "f4": "diff't"}
    >>> compute_one_matrix(data, slice_align)
    ({'f1': [(slice(0, 4, None), 0)], 'f4': [(slice(0, 6, None), 1)]}, [[0.0, -0.8], [-0.8, 0.0]])

    If there are partial similarities, the matrix picks those up.

    >>> data = {"f1": "form", "f4": "diff't", "f5": "diff't+folm"}
    >>> compute_one_matrix(data, slice_align)
    ({'f1': [(slice(0, 4, None), 0)], 'f4': [(slice(0, 6, None), 1)], 'f5': [(slice(0, 6, None), 2), (slice(7, 11, None), 3)]}, [[0.0, -0.8, -0.8, 1.0], [-0.8, 0.0, 1.0, -0.8], [-0.8, 1.0, 0.0, 1.0], [1.0, -0.8, 1.0, 0.0]])


    """
    # First assemble all morphemes. The first int is the index of the morpheme
    # in the form, the second int is the index of the morpheme in the pairwise
    # matrix.
    trace: t.MutableMapping[types.Form_ID, t.List[t.Tuple[slice, int]]] = {
        idx: [] for idx in tokens_by_index
    }

    n_morphemes = 0
    for idx, tokens in tokens_by_index.items():
        # We need the morpheme slices, for access to prosodic strings.
        for i, slc in enumerate(get_slices(tokens)):
            trace[idx].append((slc, n_morphemes))
            n_morphemes += 1

    # Now, iterate for each string pair, assess the scores, and make sure we
    # only assign the best of those to the matrix

    matrix = [[0.0 for _ in range(n_morphemes)] for _ in range(n_morphemes)]

    # reset the self-constraints (we missed it before)
    for (idxA, morphemesA), (idxB, morphemesB) in itertools.combinations(
        trace.items(), r=2
    ):
        # iterate over all parts
        scores = []
        idxs = []
        for sliceA, posA in morphemesA:
            for sliceB, posB in morphemesB:
                d = align_function(idxA, idxB, sliceA, sliceB)
                scores += [d]
                idxs += [(posA, posB)]

        visited_seqs = set([])
        while scores:
            min_score_index = scores.index(min(scores))
            min_score = scores.pop(min_score_index)
            posA, posB = idxs.pop(min_score_index)
            if posA in visited_seqs or posB in visited_seqs:
                matrix[posA][posB] = 1.0
                matrix[posB][posA] = 1.0
            else:
                matrix[posA][posB] = min_score
                matrix[posB][posA] = min_score
                visited_seqs.add(posA)
                visited_seqs.add(posB)
    for idx in tokens_by_index:
        for i, (sliceA, posA) in enumerate(trace[idx]):
            for j, (sliceB, posB) in enumerate(trace[idx]):
                if i < j:
                    matrix[posA][posB] = 1.0
                    matrix[posB][posA] = 1.0
    return trace, matrix


def get_partial_matrices(
    self,
    concepts: t.Iterable[types.Parameter_ID],
    method="lexstat",
    scale=0.5,
    factor=0.3,
    mode="global",
) -> t.Iterator[
    t.Tuple[
        types.Parameter_ID,
        t.Mapping[t.Hashable, t.List[t.Tuple[slice, int]]],
        t.List[t.List[float]],
    ]
]:
    """
    Function creates matrices for the purpose of partial cognate detection.
    """
    if method != "lexstat":
        raise ValueError(f"Method {method} unknown.")

    def function(idxA, idxB, sA: slice, sB: slice):
        almA, almB, sim = alignment_functions[mode](
            self[idxA, self._numbers][sA],
            self[idxB, self._numbers][sB],
            [
                self.cscorer[_charstring(self[idxB, self._langid]), n]
                for n in self[idxA, self._numbers][sA]
            ],
            [
                self.cscorer[_charstring(self[idxA, self._langid]), n]
                for n in self[idxB, self._numbers][sB]
            ],
            self[idxA, self._prostrings][sA],
            self[idxB, self._prostrings][sB],
            sA.stop - sA.start,
            sB.stop - sB.start,
            scale,
            factor,
            self.cscorer,
        )
        simA = sum(
            [(1.0 + factor) * self.cscorer[i, i] for i in self[idxA, self._numbers][sA]]
        )
        simB = sum(
            [(1.0 + factor) * self.cscorer[i, i] for i in self[idxB, self._numbers][sB]]
        )
        return 1 - ((2 * sim) / (simA + simB))

    # We have two basic constraints in the algorithm:
    # a) Morphemes in the same word are not cognate
    # b) Morphemes can be cognate with only (at most) one morpheme in another word
    #
    # “Not cognate” means setting values to 1 here, since we are dealing with
    # normalized distances.
    for c in concepts:
        indices = self.get_list(row=c, flat=True)
        tokens_by_index = {idx: self[idx, self._segments] for idx in indices}
        yield c, *compute_one_matrix(
            tokens_by_index=tokens_by_index, align_function=function
        )


def partial_cluster(
    self,
    method="sca",
    threshold=0.45,
    scale=0.5,
    factor=0.3,
    mode="overlap",
    cluster_function=lingpy.algorithm.extra.infomap_clustering,
) -> t.Iterable[t.Tuple[t.Hashable, slice, int]]:

    # check for parameters and add clustering, in order to make sure that
    # analyses are not repeated

    concepts = sorted(self.rows)

    min_concept_cognateset = 0
    for concept, morphemes, matrix in cli.tq(
        get_partial_matrices(
            self,
            concepts,
            method=method,
            scale=scale,
            factor=factor,
            mode=mode,
        ),
        "partial sequence clustering",
    ):
        c = cluster_function(
            threshold, matrix, taxa=list(range(len(matrix))), revert=True
        )
        for form, form_morphemes in morphemes.items():
            for slice, matrix_index in form_morphemes:
                yield form, slice, c[matrix_index] + min_concept_cognateset

        min_concept_cognateset += len(matrix) + 1


def cognate_code_to_file(
    dataset: types.Wordlist,
    ratio: float,
    soundclass: str,
    cluster_method: str,
    threshold: float,
    initial_threshold: float,
    gop: float,
    mode: str,
    output_file: Path,
) -> None:
    assert (
        dataset.column_names.forms.segments is not None
    ), "Dataset must have a CLDF #segments column."

    lex = lingpy.compare.partial.Partial.from_cldf(
        dataset.tablegroup._fname,
        filter=filter_function_factory(dataset),
        columns=["doculect", "concept", "tokens"],
        model=lingpy.data.model.Model(soundclass),
        check=True,
    )

    if ratio != 1.5:
        if ratio == float("inf"):
            ratio_pair = (1, 0)
            ratio_str = "-inf"
        if ratio == int(ratio) >= 0:
            r = int(ratio)
            ratio_pair = (r, 1)
            ratio_str = "-{:d}".format(r)
        elif ratio > 0:
            ratio_pair = (ratio, 1)
            ratio_str = "-" + str(ratio)
        else:
            raise ValueError("LexStat ratio must be in [0, ∞]")
    else:
        ratio_pair = (3, 2)
        ratio_str = ""
    if initial_threshold != 0.7:
        ratio_str += "-t{:02d}".format(int(initial_threshold * 100))
    try:
        scorers_etc = lingpy.compare.lexstat.LexStat(
            filename="lexstats-{:}-{:s}{:s}.tsv".format(
                sha1(dataset.tablegroup._fname), soundclass, ratio_str
            )
        )
        lex.scorer = scorers_etc.scorer
        lex.cscorer = scorers_etc.cscorer
        lex.bscorer = scorers_etc.bscorer
    except (OSError, ValueError):
        lex.get_scorer(runs=10000, ratio=ratio_pair, threshold=initial_threshold)
        lex.output(
            "tsv",
            filename="lexstats-{:}-{:s}{:s}".format(
                sha1(dataset.tablegroup._fname), soundclass, ratio_str
            ),
            ignore=[],
        )
    # For some purposes it is useful to have monolithic cognate classes.
    lex.cluster(
        method="lexstat",
        threshold=threshold,
        ref="cogid",
        cluster_method=cluster_method,
        verbose=True,
        override=True,
        gop=gop,
        mode=mode,
    )
    # But actually, in most cases partial cognates are much more useful.
    partial_cluster(
        lex,
        method="lexstat",
        threshold=threshold,
        ref="partialcognateids",
        gop=gop,
        mode=mode,
    )
    lex.output("tsv", filename="auto-clusters")
    alm = lingpy.Alignments(lex, ref="partialcognateids", fuzzy=True)
    alm.align(method="progressive")
    alm.output("tsv", filename=str(output_file), ignore="all", prettify=False)


# TODO: This should have quite a lot of overlapping functionality with
# lexedata.importer.cognates, and should be consolidated.
def import_back(dataset, output_file):
    try:
        dataset.add_component("CognateTable")
    except ValueError:
        ...
    try:
        dataset.add_component("CognatesetTable")
    except ValueError:
        ...

    read_back = csv.DictReader(
        open(str(output_file) + ".tsv", encoding="utf-8"), delimiter="\t"
    )
    cognatesets = {}
    judgements = []
    i = 1
    for line in read_back:
        partial = line["PARTIALCOGNATEIDS"].split()
        alignment = line["ALIGNMENT"].split(" + ")
        slice_start = 0
        for cs, alm in zip(partial, alignment):
            # TODO: @Gereon: is it alright to add the same content to Name and ID?
            cognatesets.setdefault(cs, {"ID": cs, "Name": cs})
            length = len(alm.split())
            judgements.append(
                {
                    "ID": i,
                    "Form_ID": line["ID"],
                    "Cognateset_ID": cs,
                    "Segment_Slice": [
                        "{:d}:{:d}".format(slice_start, slice_start + length)
                    ],
                    "Alignment": alm.split(),
                    "Source": ["LexStat"],
                }
            )
            i += 1
            slice_start += length
    dataset.write(CognatesetTable=cognatesets.values())
    dataset.write(CognateTable=judgements)


if __name__ == "__main__":
    parser = cli.parser(__package__ + "." + Path(__file__).stem, description=__doc__)
    parser.add_argument(
        "--output-file",
        "-o",
        type=Path,
        default="aligned",
        help="Output file to write segmented data to,"
        " without extension .tsv (automatically added) (default: aligned)",
    )
    parser.add_argument(
        "--sound-class",
        default="sca",
        choices=["sca", "dolgo", "asjp", "art"],
        help="Sound class model to use (default: sca)",
    )
    parser.add_argument(
        "--threshold",
        default=0.55,
        type=float,
        help="Cognate clustering threshold value (default: 0.55)",
    )
    parser.add_argument(
        "--clustering-method",
        default="infomap",
        help="Cognate clustering method name. Valid options"
        " are, dependent on your LingPy version, {'upgma',"
        " 'single', 'complete', 'mcl', 'infomap'}."
        " (default: infomap)",
    )
    parser.add_argument(
        "--gop",
        default=-2,
        type=float,
        help="Gap opening penalty for the clustering procedure (default: -2)",
    )
    parser.add_argument(
        "--mode",
        default="overlap",
        choices=["global", "local", "overlap", "dialign"],
        help="Select the mode for the alignment analysis (default: overlap)",
    )
    parser.add_argument(
        "--ratio",
        default=1.5,
        type=float,
        help="Ratio of language-pair specific vs. general"
        " scores in the LexStat algorithm (default: 1.5)",
    )
    parser.add_argument(
        "--initial-threshold",
        default=0.7,
        type=float,
        help="Threshold value for the initial pairs used to"
        " bootstrap the calculation (default: 0.7)",
    )
    args = parser.parse_args()

    dataset = pycldf.Wordlist.from_metadata(args.metadata)
    cognate_code_to_file(
        dataset=dataset,
        ratio=args.ratio,
        cluster_method=args.clustering_method,
        soundclass=args.sound_class,
        mode=args.mode,
        threshold=args.threshold,
        initial_threshold=args.initial_threshold,
        gop=args.gop,
        output_file=args.output_file,
    )
    import_back(dataset=dataset, output_file=args.output_file)
