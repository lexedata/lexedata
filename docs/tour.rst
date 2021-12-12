==================
A tour of lexedata
==================

This tutorial will take you on a tour through the command line functionality of
the lexedata package. We will start with a small lexical dataset in an
interleaved tabular format, where each column corresponds to a language and each
pair of rows to a concept, with preliminary cognate codes. We will take you
through turning the data set into CLDF, editing cognate judgements, and
exporting the data set as phylogenetic alignment.

(To prevent this tutorial from becoming obsolete, our continuous integration
testing system ‘follows’ this tutorial when we update the software. So if it
appears overly verbose or rigid to you at times, it's because it has a secondary
function as test case. This is also the reason we use the command line where we
can, even in places where a GUI tool would be handy: Our continuous integration
tester cannot use the GUI.) ::

Lexedata is a collection of command line tools. If you have never worked on the
command line before, check out `our quick primer on the command line`_. This
tutorial further assumes you have a working `installation of lexedata`_ and
`git`_. The tutorial will manipulate the Git repository using Git's command line
interface, but you can use a Git GUI instead. (Not using version control for
your data is dangerous, because lexedata does not include an ‘undo’ function.)

Importing a dataset into CLDF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, create a new empty directory. We will collect the data and run
the analyses inside that folder. Open a command line interface, and
make sure its working directory is that new folder. For example,
start terminal and execute ::

    $ mkdir bantu
    $ cd bantu

For this tutorial, we will be using lexical data from the Bantu family,
collected by XXX. The data is stored in an Excel file which you can download
from the lexedata repository ::

    $ curl -L https://github.com/Anaphory/lexedata/blob/master/test/data/excel/small.xlsx?raw=true -o bantu.xlsx
    [... Download progress]
    $ cp ~/Develop/lexedata/docs/examples/bantu.xlsx bantu.xlsx

(curl is a command line tool to download files from URLs, available
under Linux and Windows. You can, of course, download the file
yourself using whatever method you are most comfortable with, and save
it as ``Bantu.xlsx`` in this folder.)

If you look at this data, you will see that ::

    $ python -c 'from openpyxl import load_workbook
    > for row in load_workbook("bantu.xlsx").active.iter_rows():
    >   print(*[c.value or "" for c in row], sep="\t")'
    [...]

it is table with one column for each language, and every pair of rows contains
the data for one concept. The first row of each pair contains the forms for the
concept (a cell can have multiple forms separated by comma), and the second row
contains cognacy judgements for those forms.

This is one of several formats supported by lexedata for import. The
corresponding importer is called `excel_interleaved` and it works like this::

    $ python -m lexedata.importer.excel_interleaved --help
    usage: excel_interleaved.py [-h] [--sheet SHEET] [--directory DIRECTORY]
                                [--loglevel LOGLEVEL] [-q] [-v]
                                EXCEL

    Import data in the "interleaved" format from an xls spreadsheet [...]

    positional arguments:
      EXCEL                 The Excel file to parse

    optional arguments:
      -h, --help            show this help message and exit
      --sheet SHEET         Excel sheet name(s) to import (default: all sheets)
      --directory DIRECTORY
                            Path to directory where forms.csv is created (default:
                            current working directory)

    Logging:
      --loglevel LOGLEVEL
      -q
      -v

So this importer needs to be told about the Excel file to import, and it can be
told about the destination directory of the import and about sheet names to
import, eg. if your Excel file contains additional non-wordlist data in separate
worksheets.

Like nearly every lexedata scripts, this one has logging controls to change the
verbosity. There are 5 levels of logging: CRITICAL, ERROR, WARNING, INFO, and
DEBUG. Normally, scripts operate on the INFO level: They are tell us about
anything that might be relevant about the progress and successes. If that's too
much output, you can make it *-q*-uieter to only display warnings, which tell us
about anthing where the script found data not up to standard and had to fall
back to some workaround to proceed. Even less output happens on the ERROR level
(“Your data had issues that made me unable to complete the current step, but I
can still recover to do *something* more”) and the CRITICAL level (“I found
something that makes me unable to proceed at all.”). We run many of the examples
here in quiet mode, you probably don't want to do that.

With that in mind, we can run the interleaved importer simply with the Excel
file as argument::

    $ python -m lexedata.importer.excel_interleaved -q bantu.xlsx
    WARNING:lexedata:Cell N16 was empty, but cognatesets ? were given in N17.

This shows a few minor issues in the data, but the import has succeeded, giving
us a FormTable in the file ``forms.csv``::

    $ head forms.csv
    ID,Language_ID,Parameter_ID,Form,Comment,Cognateset_ID
    duala_all,Duala,all,ɓɛ́sɛ̃,,1
    duala_arm,Duala,arm,dia,,7
    duala_ashes,Duala,ashes,mabúdú,,17
    duala_bark,Duala,bark,bwelé,,23
    duala_belly,Duala,belly,dibum,,1
    duala_big,Duala,big,éndɛ̃nɛ̀,,1
    duala_bird,Duala,bird,inɔ̌n,,1
    duala_bite,Duala,bite,kukwa,,6
    duala_black,Duala,black,wínda,,21

A well-structured ``forms.cvs`` is a valid, `“metadata-free”`_ CLDF wordlist. In
this case, the data contains a column that CLDF does not know out-of-the-box,
but otherwise the dataset is fine. ::

    $ cldf validate forms.csv 
    [...] UserWarning: Unspecified column "Cognateset_ID" in table forms.csv
      warnings.warn(

Working with git
~~~~~~~~~~~~~~~~

This is the point where it really makes sense to start working with ``git``.
(This aspect is still missing from this tutorial.)

Adding metadata and explicit tables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A better structure for a lexical dataset – or any dataset, really – is to
provide metadata. A CLDF dataset is described by a metadata file in JSON format.
You can write such a file by hand in any text editor, but lexedata comes with a
script that is able to guess some properties of the dataset and give you a
metadata file template. ::

    $ python -m lexedata.edit.add_metadata
    INFO:lexedata:CLDF freely understood the columns ['Comment', 'Form', 'ID', 'Language_ID', 'Parameter_ID'] in your forms.csv.
    INFO:lexedata:Column Cognateset_ID seems to be a http://cldf.clld.org/v1.0/terms.rdf#cognatesetReference column.
    INFO:lexedata:Also added column Segments, as expected for a FormTable.
    INFO:lexedata:Also added column Source, as expected for a FormTable.
    INFO:lexedata:FormTable re-written.

Lexedata has recognized the cognate judgement column correctly as what it is and
also added two new columns to the dataset for sources (so we can track the
origin of the data in a well-structured way) and for phonemic segmentation,
which is useful in particular when working with sound correspondences on a
segment-by-segment level. We will add segments in `a future section`_.

With the new metadata file and the new columns, the data set now looks like this::

    $ ls
    bantu.xlsx
    forms.csv
    Wordlist-metadata.json
    $ cldf validate Wordlist-metadata.json
    $ head Wordlist-metadata.json
    {
        "@context": [
            "http://www.w3.org/ns/csvw",
            {
                "@language": "en"
            }
        ],
        "dc:conformsTo": "http://cldf.clld.org/v1.0/terms.rdf#Wordlist",
        "dc:contributor": [
            "https://github.com/Anaphory/lexedata/blob/master/src/lexedata/edit/add_metadata.py"
    $ head forms.csv
    ID,Language_ID,Parameter_ID,Form,Comment,Cognateset_ID,Segments,Source
    duala_all,Duala,all,ɓɛ́sɛ̃,,1,,
    duala_arm,Duala,arm,dia,,7,,
    duala_ashes,Duala,ashes,mabúdú,,17,,
    duala_bark,Duala,bark,bwelé,,23,,
    duala_belly,Duala,belly,dibum,,1,,
    duala_big,Duala,big,éndɛ̃nɛ̀,,1,,
    duala_bird,Duala,bird,inɔ̌n,,1,,
    duala_bite,Duala,bite,kukwa,,6,,
    duala_black,Duala,black,wínda,,21,,

The ``cldf validate`` script only outputs problems, so if it prints out nothing,
it means that the data set conforms to the CLDF standard!

Now that we have a good starting point, we can start working with the data and
improving it. First, we change the template metadata file to include an actual
description of what most people might understand when we say “metadata”:
Authors, provenience, etc.

    ::

        {
            "@context": [
                "http://www.w3.org/ns/csvw",
                {
                    "@language": "en"
                }
            ],
            "dc:conformsTo": "http://cldf.clld.org/v1.0/terms.rdf#Wordlist",
            "dc:contributor": [
                "https://github.com/Anaphory/lexedata/blob/master/src/lexedata/edit/add_metadata.py"
            ],
            "dialect": {
                "commentPrefix": null
            },
            "tables": [
                {
                    "dc:conformsTo": "http://cldf.clld.org/v1.0/terms.rdf#FormTable",
                    "dc:extent": 1592,
                    "tableSchema": {
                        "columns": [
                            {
                                "datatype": {
                                    "base": "string",
                                    "format": "[a-zA-Z0-9_-]+"
                                },
                                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#id",
                                "required": true,
                                "name": "ID"
                            },
                            {
                                "dc:description": "A reference to a language (or variety) the form belongs to",
                                "dc:extent": "singlevalued",
                                "datatype": "string",
                                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#languageReference",
                                "required": true,
                                "name": "Language_ID"
                            },
                            {
                                "dc:description": "A reference to the meaning denoted by the form",
                                "datatype": "string",
                                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#parameterReference",
                                "required": true,
                                "name": "Parameter_ID"
                            },
                            {
                                "dc:description": "The written expression of the form. If possible the transcription system used for the written form should be described in CLDF metadata (e.g. via adding a common property `dc:conformsTo` to the column description using concept URLs of the GOLD Ontology (such as [phonemicRep](http://linguistics-ontology.org/gold/2010/phonemicRep) or [phoneticRep](http://linguistics-ontology.org/gold/2010/phoneticRep)) as values).",
                                "dc:extent": "singlevalued",
                                "datatype": "string",
                                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#form",
                                "required": true,
                                "name": "Form"
                            },
                            {
                                "datatype": "string",
                                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#comment",
                                "required": false,
                                "name": "Comment"
                            },
                            {
                                "datatype": "string",
                                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#cognatesetReference",
                                "name": "Cognateset_ID"
                            },
                            {
                                "dc:extent": "multivalued",
                                "datatype": "string",
                                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#segments",
                                "required": false,
                                "separator": " ",
                                "name": "Segments"
                            },
                            {
                                "datatype": "string",
                                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#source",
                                "required": false,
                                "separator": ";",
                                "name": "Source"
                            }
                        ],
                        "primaryKey": [
                            "ID"
                        ]
                    },
                    "url": "forms.csv"
                }
            ]
        }

    -- Wordlist-metadata.json

Another useful step is to make languages, concepts, and cognate codes explicit.
Currently, all the dataset knows about these their names. We can generate a
scaffold for metadata about languages etc. with another tool. ::

    $ python -m lexedata.edit.add_table LanguageTable
    INFO:lexedata:Found 14 different entries for your new LanguageTable.
    $ python -m lexedata.edit.add_table ParameterTable
    INFO:lexedata:Found 100 different entries for your new ParameterTable.
    WARNING:lexedata:Some of your reference values are not valid as IDs: ['go to', 'rain (v)', 'sick, be', 'sleep (v)']

“Parameter” is CLDF speak for the things sampled per-language. In a
StructureDataset this might be typological features, in a Wordlist the
ParameterTable contains the concepts. The warning we will ignore for now.

Every form belongs to one language, and every language has multiple forms. This
is a simple 1:n relationship. Every form has and one or more concepts associated
to it (in this way, CLDF supports annotating polysemies) and every concept has
several forms, in different languages but also synonyms within a single
language. This can easily be reflected by entries in the FormTable.

The logic behind cognate judgements is slightly different. A form belong to one
or more cognate sets, but in addition to the cognate class, there may be
additional properties of a cognate judgement, such as alignments, segments the
judgement is about (if it is a partial cognate judgement), comments (“dubious:
m~t is unexplained”) or the source claiming the etymological relationship.
Because of this, there is a separate table for cognate judgements, the
CognateTable, and *that* table then refers to a CognatesetTable we can make
explicit. ::

    $ python -m lexedata.edit.add_cognate_table
    CRITICAL:lexedata:You must specify whether cognateset have dataset-wide unique ids or not (--unique-id)

In our example dataset, cognate class “1” for all is not cognate with class “1”
for arm, so we need to tell ``add_cognate_table`` that these IDs are only unique
within a concept::

    $ python -m lexedata.edit.add_cognate_table -q --unique-id concept
    $ python -m lexedata.edit.add_table CognatesetTable
    INFO:lexedata:Found 651 different entries for your new CognatesetTable.

Now all the external properties of a form can be annotated with explicit
metadata in their own table files, for example for the languages:

    ::

        ID,Name,Macroarea,Latitude,Longitude,Glottocode,ISO639P3code
        Bushoong,Bushoong,,,,,
        Duala,Duala,,,,,
        Fwe,Fwe,,,,,
        Ha,Ha,,,,,
        Kikuyu,Kikuyu,,,,,
        Kiyombi,Kiyombi,,,,,
        Lega,Lega,,,,,
        Luganda,Luganda,,,,,
        Ngombe,Ngombe,,,,,
        Ntomba,Ntomba,,,,,
        Nyamwezi,Nyamwezi,,,,,
        Nzadi,Nzadi,,,,,
        Nzebi,Nzebi,,,,,
        Swahili,Swahili,,,,,

    -- languages.csv

If you edit files by hand, it's always good to check CLDF compliance afterwards
– small typos are just too easy to make, and they don't catch the eye. ::
    
    $ cldf validate Wordlist-metadata.json
    WARNING parameters.csv:37:1 ID: invalid lexical value for string: go to
    WARNING parameters.csv:70:1 ID: invalid lexical value for string: rain (v)
    WARNING parameters.csv:77:1 ID: invalid lexical value for string: sick, be
    WARNING parameters.csv:80:1 ID: invalid lexical value for string: sleep (v)
    WARNING parameters.csv:37:1 ID: invalid lexical value for string: go to
    WARNING parameters.csv:70:1 ID: invalid lexical value for string: rain (v)
    WARNING parameters.csv:77:1 ID: invalid lexical value for string: sick, be
    WARNING parameters.csv:80:1 ID: invalid lexical value for string: sleep (v)
    WARNING forms.csv:39 Key `go to` not found in table parameters.csv
    WARNING forms.csv:72 Key `rain (v)` not found in table parameters.csv
    WARNING forms.csv:79 Key `sick, be` not found in table parameters.csv
    WARNING forms.csv:82 Key `sleep (v)` not found in table parameters.csv
    [...]

Ah, we had been warned about something like this above. We can easily fix this
by removing the 'format' restriction from ParameterTable's ID column::

    $ patch -u --verbose > /dev/null << EOF
    > --- Wordlist-metadata.json	2021-12-12 02:04:28.519080902 +0100
    > +++ Wordlist-metadata.json~	2021-12-12 02:05:36.161817085 +0100
    > @@ -181,8 +181,7 @@
    >                  "columns": [
    >                      {
    >                          "datatype": {
    > -                            "base": "string",
    > -                            "format": "[a-zA-Z0-9_\\\-]+"
    > +                            "base": "string"
    >                          },
    >                          "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#id",
    >                          "required": true,
    > @@ -329,4 +328,4 @@
    >              "url": "cognatesets.csv"
    >          }
    >      ]
    > -}
    > \ No newline at end of file
    > +}
    > EOF

Extended extended CLDF compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We have taken this dataset from a somewhat ideosyncratic format to metadata-free
CLDF and to a dataset with extended CLDF compliance. The ``cldf validate``
script checks for strict conformance with the CLDF standard. However, there are
some assumptions which lexedata and also some other CLDF-aware tools tend to
make which are not strictly mandated by the CLDF specifications. One such
assumption is the one that led to the issue above:

    Each CLDF data table SHOULD contain a column which uniquely identifies a row
    in the table. This column SHOULD be marked using:

     - a propertyUrl of http://cldf.cld.org/v1.0/terms.rdf#id
     - the column name ID in the case of metadata-free conformance.

    To allow usage of identifiers as path components of URIs and ensure they are
    portable across systems, identifiers SHOULD be composed of alphanumeric
    characters, underscore ``_`` and hyphen ``-`` only, i.e. match the regular
    expression ``[a-zA-Z0-9\-_]+`` (see RFC 3986).

    -- https://github.com/cldf/cldf#identifier

Because of the potential use in URLs, our table adder adds tables with the ID
format that we encountered above. This specification uses the word 'SHOULD', not
'MUST', which `allows to ignore the requirement in certain circumstances`_
(https://datatracker.ietf.org/doc/html/rfc2119#section-3) and thus ``cldf
validate`` does not enforce it. We have however a separate report script that
points out this and other deviations from sensible assumptions. ::

    $ python -m lexedata.report.extended_cldf_validate
    WARNING:lexedata:Table parameters.csv has an unconstrained ID column ID. Consider setting its format to [a-zA-Z0-9_-]+ and/or running `lexedata.edit.simplify_ids`.
    [...]

We can fix this using another tool from the lexedata toolbox. ::

    $ python -m lexedata.edit.simplify_ids --table parameters.csv
    INFO:lexedata:Handling table parameters.csv…
    [...]

Merging polysemous forms
~~~~~~~~~~~~~~~~~~~~~~~~

…

