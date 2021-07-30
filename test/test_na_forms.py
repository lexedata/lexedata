"""Test Lexedata handling of NA values

In https://github.com/cldf/cldf/issues/108, we started a discussion concerning
different types of NA values in lexical data.

CLDF formalizes the following distinction:

> Data creators often want to distinguish two kinds of missing data, in
> particular when the data is extracted from sources:
>
> 1. data that is missing/unknown because it was never extracted from the source,
> 2. data that is indicated in the source as unknown.
>
> The CSVW data model can be used to express this difference as follows: Case 1
> can be modeled by not including the relevant data as row at all. Case 2 can
> be modeled using the null property of the relevant column specification as
> value in a data row.

There is, however, a third case: Data where the source states that the
parameter value is not applicable to the language. We encode this generally by
"-", but our goal is to in the end also accept other non-empty strings that
contain no alphabetical characters, in particular "/" and "–".

Some source datasets use "?" to indicate cases 1 and 2, this needs to be
handled upon import.

Special handling of these three different NA forms alongside valid forms is
tested by this module. It affects multiple different components of Lexedata.

"""


def test_import_skips_question_marks():
    data = [  # noqa
        ["Concept", "L1", "L2"],
        ["C1", "?", "Form1"],
        ["C2", "Form2", "Form3"],
    ]
    # TODO: Put data into an Excel sheet
    # TODO: Run a matrix importer
    # TODO: Check that the resulting dataset has no entry for C1 in L1


def test_import_loads_dash():
    data = [  # noqa
        ["Concept", "L1", "L2"],
        ["C1", "-", "Form1"],
        ["C2", "Form2", "Form3"],
    ]  # noqa
    # TODO: Put data into an Excel sheet
    # TODO: Run a matrix importer
    # TODO: Check that the resulting dataset has an entry "-" for C1 in L1


def test_phylogenetics_exporter_dash_is_absence():
    forms = [  # noqa
        {"ID": "L1C1", "Language_ID": "L1", "Concept_ID": "C1", "Form": "L1C1"},
        {"ID": "L2C1", "Language_ID": "L2", "Concept_ID": "C1", "Form": "L2C1"},
        {"ID": "L1C2", "Language_ID": "L1", "Concept_ID": "C2", "Form": "L1C2"},
        {"ID": "L2C2", "Language_ID": "L2", "Concept_ID": "C2", "Form": "-"},
    ]
    cognates = [  # noqa
        {"Form_ID": "L1C1", "Cognateset_ID": "1"},
        {"Form_ID": "L2C1", "Cognateset_ID": "1"},
        {"Form_ID": "L1C2", "Cognateset_ID": "2"},
    ]
    # TODO: Run the phylogenetics exporter
    assert {"L1": "011", "L2": "010"}  # TODO == alignment


def test_phylogenetics_exporter_unknown():
    forms = [  # noqa
        {"ID": "L1C1", "Language_ID": "L1", "Concept_ID": "C1", "Form": "L1C1"},
        {"ID": "L2C1", "Language_ID": "L2", "Concept_ID": "C1", "Form": "L2C1"},
        {"ID": "L1C2", "Language_ID": "L1", "Concept_ID": "C2", "Form": "L1C2"},
        {"ID": "L2C2", "Language_ID": "L2", "Concept_ID": "C2", "Form": ""},
        {"ID": "L2C3", "Language_ID": "L2", "Concept_ID": "C3", "Form": "L1C3"},
    ]
    cognates = [  # noqa
        {"Form_ID": "L1C1", "Cognateset_ID": "1"},
        {"Form_ID": "L2C1", "Cognateset_ID": "1"},
        {"Form_ID": "L1C2", "Cognateset_ID": "2"},
        {"Form_ID": "L1C3", "Cognateset_ID": "3"},
    ]
    # TODO: Run the phylogenetics exporter
    assert {"L1": "011?", "L2": "01?1"}  # TODO == alignment


def test_edictor_no_na_forms():
    forms = [  # noqa
        {"ID": "L1C1", "Language_ID": "L1", "Concept_ID": "C1", "Form": ""},
        {"ID": "L2C1", "Language_ID": "L2", "Concept_ID": "C1", "Form": "L2C1"},
        {"ID": "L1C2", "Language_ID": "L1", "Concept_ID": "C2", "Form": "L1C2"},
        {"ID": "L2C2", "Language_ID": "L2", "Concept_ID": "C2", "Form": "-"},
    ]
    cognates = [  # noqa
        {"Form_ID": "L2C1", "Cognateset_ID": "1"},
        {"Form_ID": "L1C2", "Cognateset_ID": "2"},
    ]
    # TODO: Run the edictor exporter
    # TODO: Check that the edictor export contains only L2C1 and L1C2


def test_detect_cognates_ignores_na_forms():
    forms = [  # noqa
        {"ID": "L1C1", "Language_ID": "L1", "Concept_ID": "C1", "Form": ""},
        {"ID": "L2C1", "Language_ID": "L2", "Concept_ID": "C1", "Form": "L2C1"},
        {"ID": "L1C2", "Language_ID": "L1", "Concept_ID": "C2", "Form": "L1C2"},
        {"ID": "L2C2", "Language_ID": "L2", "Concept_ID": "C2", "Form": "-"},
    ]
    # TODO: run ACD
    # TODO: Check that the cognatesets contain only L2C1 and L1C2
    cognates = [  # noqa
        {"Form_ID": "L2C1", "Cognateset_ID": "1"},
        {"Form_ID": "L1C2", "Cognateset_ID": "2"},
    ]


def test_add_segments_skips_na_forms():
    forms = [  # noqa
        {"ID": "L1C1", "Language_ID": "L1", "Concept_ID": "C1", "Form": ""},
        {"ID": "L2C1", "Language_ID": "L2", "Concept_ID": "C1", "Form": "L2C1"},
        {"ID": "L1C2", "Language_ID": "L1", "Concept_ID": "C2", "Form": "L1C2"},
        {"ID": "L2C2", "Language_ID": "L2", "Concept_ID": "C2", "Form": "-"},
    ]
    # TODO: run add_segments
    # TODO: Check that the segments for L1C1 and L2C2 are empty


def test_add_singlestons():
    forms = [  # noqa
        {"ID": "L1C1", "Language_ID": "L1", "Concept_ID": "C1", "Form": ""},
        {"ID": "L2C1", "Language_ID": "L2", "Concept_ID": "C1", "Form": "L2C1"},
        {"ID": "L1C2", "Language_ID": "L1", "Concept_ID": "C2", "Form": "L1C2"},
        {"ID": "L2C2", "Language_ID": "L2", "Concept_ID": "C2", "Form": "-"},
    ]
    # TODO: run add_singleton_cognatesets
    # TODO: Check that there is no cognate set for L1C1
    # TODO: What should happen to the -?


def test_homohpones_skips_na_forms():
    forms = [  # noqa
        {"ID": "L1C1", "Language_ID": "L1", "Concept_ID": "C2", "Form": "form"},
        {"ID": "L1C2", "Language_ID": "L1", "Concept_ID": "C1", "Form": ""},
        {"ID": "L1C3", "Language_ID": "L1", "Concept_ID": "C2", "Form": "form"},
        {"ID": "L1C4", "Language_ID": "L1", "Concept_ID": "C2", "Form": ""},
        {"ID": "L1C5", "Language_ID": "L1", "Concept_ID": "C2", "Form": "-"},
        {"ID": "L1C6", "Language_ID": "L2", "Concept_ID": "C2", "Form": "-"},
    ]
    # TODO: run report.homophones
    # TODO: check that the reported homophones are only [{"L1C1", "L1C3"}], because the other entries don't count as forms.


def test_extended_cldf_validate():
    # TODO: What tests should this run? What kind of data should fail?
    # - A dataset where an NA form is in cognatesets should fail
    # - A dataset where the segments is "" and the form is "-" should pass
    ...


def test_coverage_reports_na():
    # TODO: Check that the coverage report can treat "" forms like missing
    # rows, and that it can report "-" forms separately, and that it counts
    # neither of these two as present forms.
    ...
