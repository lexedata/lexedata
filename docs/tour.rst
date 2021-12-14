##################
A tour of lexedata
##################

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

    $ python -m lexedata.importer.excel_interleaved --help
    [...]
    $ export LANG=C

Lexedata is a collection of command line tools. If you have never worked on the
command line before, check out :doc:`our quick primer on the command line <cli>`. This
tutorial further assumes you have a working :doc:`installation of lexedata <install>` and
:doc:`git`. The tutorial will manipulate the Git repository using Git's command line
interface, but you can use a Git GUI instead. (Not using version control for
your data is dangerous, because lexedata does not include an ‘undo’ function.)

*****************************
Importing a dataset into CLDF
*****************************

First, create a new empty directory. We will collect the data and run
the analyses inside that folder. Open a command line interface, and
make sure its working directory is that new folder. For example,
start terminal and execute ::

    $ mkdir bantu
    $ cd bantu

For this tutorial, we will be using lexical data from the Bantu family,
collected by Hilde Gunnink. The data set is a subset of an earlier version 
(deliberately, so this tour can show some steps in the cleaning process) of her lexical dataset.
The data is stored in an Excel file which you can download from
the lexedata repository ::

    $ curl -L https://github.com/Anaphory/lexedata/blob/scriptdoctest/docs/examples/bantu.xlsx?raw=true -o bantu.xlsx
    [... Download progress]

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
corresponding importer is called ``excel_interleaved`` and it works like this::

    $ python -m lexedata.importer.excel_interleaved --help
    usage: excel_interleaved.py [-h] [--sheet SHEET] [--directory DIRECTORY]
                                [--loglevel LOGLEVEL] [-q] [-v]
                                EXCEL

    Import data in the "interleaved" format from an xls spreadsheet [...]
    [...]

    positional arguments:
      EXCEL                 The Excel file to parse

    option[...]:
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

A well-structured ``forms.cvs`` is a valid, `“metadata-free”
<https://github.com/cldf/cldf#metadata-free-conformance>`_ CLDF wordlist. In
this case, the data contains a column that CLDF does not know out-of-the-box,
but otherwise the dataset is fine. ::

    $ cldf validate forms.csv 
    [...] UserWarning: Unspecified column "Cognateset_ID" in table forms.csv
      warnings.warn(

Working with git
================

This is the point where it really makes sense to start working with ``git``. ::

    $ git init
    [...]
    Initialized empty Git repository in [...]bantu/.git/
    $ git config user.name 'Lexedata'
    $ git config user.email 'lexedata@example.com'
    $ git add forms.csv
    $ git commit -m "Initial import"
    [master (root-commit) [...]] Initial import
     1 file changed, 1593 insertions(+)
     create mode 100644 forms.csv

Adding metadata and explicit tables
===================================

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
segment-by-segment level. We will add segments in :ref:`a future section <segments>`.

With the new metadata file and the new columns, the data set now looks like this::

    $ ls
    Wordlist-metadata.json
    bantu.xlsx
    forms.csv
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
it means that the data set conforms to the CLDF standard! That's a good starting
point to create a new commit. ::

    $ git add Wordlist-metadata.json
    $ git commit -m "Add metadata file"
    [master [...]] Add metadata file
     1 file changed, 87 insertions(+)
     create mode 100644 Wordlist-metadata.json

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

And commit. ::

    $ git commit -am "Add metadata"
    [...]

Adding satelite tables
-----------------------
    
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
language. This can easily be reflected by entries in the FormTable. So far, so
good. ::

    $ git add languages.csv parameters.csv
    $ git commit -am "Add language and concept tables"
    [master [...]] Add language and concept tables
     3 files changed, 246 insertions(+), 1 deletion(-)
     create mode 100644 languages.csv
     create mode 100644 parameters.csv

The logic behind cognate judgements is slightly different. A form belongs to one
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
    WARNING:lexedata:No segments found for form duala_all (ɓɛ́sɛ̃).
    WARNING:lexedata:No segments found for form duala_arm (dia).
    WARNING:lexedata:No segments found for form duala_ashes (mabúdú).
    WARNING:lexedata:No segments found for form duala_bark (bwelé).
    WARNING:lexedata:No segments found for 1585 forms. You can generate segments using `lexedata.edit.segment_using_clts`.

Clean the data
==============

The cognate table needs to represent whether some or all of a form is judged to
be cognate, and for that it needs the segments to be present. So before we
continue, we use git to undo the creation of the cognate table. ::

    $ git checkout .
    Updated 2 paths from the index

Adding segments at this stage is dangerous: Some of our forms still contain
comments etc., and as first step we should move those out of the actual `form
<https://cldf.clld.org/v1.0/terms.rdf#form>`̲ column. ::

    $ python -m lexedata.edit.clean_forms
    ERROR:lexedata:Line 962: Form 'raiha (be long' has unbalanced brackets. I did not modify the row.
    INFO:lexedata:Line 106: Split form 'lopoho ~ mpoho ~ lòpòhó' into 3 elements.
    INFO:lexedata:Line 113: Split form 'lokúa ~ nkúa' into 2 elements.
    INFO:lexedata:Line 116: Split form 'yǒmbi ~ biómbi' into 2 elements.
    INFO:lexedata:Line 154: Split form 'lopíko ~ mpíko' into 2 elements.
    INFO:lexedata:Line 162: Split form 'ngómbá ~ ngòmbá' into 2 elements.
    INFO:lexedata:Line 165: Split form 'lokála ~ nkála' into 2 elements.
    INFO:lexedata:Line 169: Split form 'moólo ~ miólo' into 2 elements.
    INFO:lexedata:Line 171: Split form 'mbókà ~ mambóka' into 2 elements.
    INFO:lexedata:Line 194: Split form 'yěmi ~ elemi' into 2 elements.
    INFO:lexedata:Line 211: Split form 'búdùlù ~ pùdùlù' into 2 elements.
    INFO:lexedata:Line 212: Split form 'émpósù ~ ímpósù' into 2 elements.
    INFO:lexedata:Line 214: Split form 'nɛ́nɛ ~ nɛ́nɛ́nɛ' into 2 elements.
    [...]
    
Good job! Sometimes the form that is more interesting for historical linguistics
may have ended up in the ‘variants’ column, but overall, this is a big
improvement.

.. _segments:
Add phonemic segments
---------------------

Then we add the segments using the dedicated script. ::

    $ python -m lexedata.edit.add_segments -q
    WARNING:lexedata:In form duala_one (line 67): Impossible sound '/' encountered in pɔ́ / ewɔ́ – You cannot use CLTS extended normalization with this script. The slash was skipped and not included in the segments.
    WARNING:lexedata:In form duala_snake (line 84): Unknown sound ' encountered in nam'a bwaba
    WARNING:lexedata:In form ngombe_all (line 210): Unknown sound ń encountered in ńsò
    WARNING:lexedata:In form ngombe_cold (line 227): Unknown sound ḿ encountered in ḿpyo
    WARNING:lexedata:In form bushoong_dog_s2 (line 363): Unknown sound m̀ encountered in m̀mbwá
    WARNING:lexedata:In form bushoong_neck_s2 (line 411): Unknown sound ʼ encountered in ikɔ́l’l
    WARNING:lexedata:In form bushoong_sleep_v (line 430): Unknown sound ' encountered in abem't
    WARNING:lexedata:In form nzebi_bone (line 564): Unknown sound š encountered in lə̀-šiʃí
    WARNING:lexedata:In form nzebi_give (line 587): Unknown sound š encountered in šɛ
    WARNING:lexedata:In form nzebi_hair (line 589): Unknown sound * encountered in lə̀-náàŋgá * náàŋgá
    WARNING:lexedata:In form nzebi_nail (line 612): Unknown sound * encountered in lə̀-ɲâdà * ɲâdà
    WARNING:lexedata:In form nzebi_path (line 618): Unknown sound * encountered in ndzilá * mà-ndzilá
    WARNING:lexedata:In form nzebi_person (line 619): Unknown sound * encountered in mùù-tù * bàà-tà
    WARNING:lexedata:In form nzebi_seed (line 627): Unknown sound š encountered in ì-šɛ̂dí
    WARNING:lexedata:In form nzadi_arm (line 655): Unknown sound ` encountered in lwǒ`
    WARNING:lexedata:In form nzadi_new_s2 (line 740): Unknown sound * encountered in odzá:ng * nzáng
    WARNING:lexedata:In form nzadi_rain_s2 (line 750): Unknown sound ɩ́ encountered in mbvɩ́l
    WARNING:lexedata:In form nzadi_tongue (line 779): Unknown sound ɩ́ encountered in lɩlɩ́m
    WARNING:lexedata:In form nzadi_tongue (line 779): Unknown sound ɩ encountered in lɩlɩ́m
    WARNING:lexedata:In form lega_woman_s2 (line 903): Unknown sound o̩ encountered in mo̩-kazi
    WARNING:lexedata:In form kikuyu_long_s2 (line 963): Unknown sound ( encountered in raiha (be long
    WARNING:lexedata:In form kikuyu_tail_s2 (line 1009): Unknown sound ' encountered in gĩ-tong'oe
    WARNING:lexedata:In form swahili_bite (line 1141): Unknown sound ' encountered in ng'ata
    | LanguageID   | Sound   |   Occurrences | Comment                                                                                     |
    |--------------+---------+---------------+---------------------------------------------------------------------------------------------|
    | Duala        |         |             1 | illegal symbol                                                                              |
    | Duala        | '       |             1 | unknown sound                                                                               |
    | Ngombe       | ń      |             1 | unknown sound                                                                               |
    | Ngombe       | ḿ      |             1 | unknown sound                                                                               |
    | Bushoong     | m̀      |             1 | unknown sound                                                                               |
    | Bushoong     | ʼ       |             1 | unknown sound                                                                               |
    | Bushoong     | '       |             1 | unknown sound                                                                               |
    | Nzebi        | š      |             3 | unknown sound                                                                               |
    | Nzebi        | *       |             4 | unknown sound                                                                               |
    | Nzadi        | ↄ       |             8 | 'ↄ' replaced by 'ɔ' in segments. Run with `--replace-form` to apply this also to the forms. |
    | Nzadi        | `       |             1 | unknown sound                                                                               |
    | Nzadi        | *       |             1 | unknown sound                                                                               |
    | Nzadi        | ɩ́      |             2 | unknown sound                                                                               |
    | Nzadi        | ɩ       |             1 | unknown sound                                                                               |
    | Lega         | o̩      |             1 | unknown sound                                                                               |
    | Kikuyu       | (       |             1 | unknown sound                                                                               |
    | Kikuyu       | '       |             1 | unknown sound                                                                               |
    | Swahili      | '       |             1 | unknown sound                                                                               |

Some of those warnings relate to unsplit forms. We should clean up a bit, and
tell ``clean_forms`` about new separators and re-run::

    $ git checkout .
    Updated 2 paths from the index
    $ sed -i.bak -e '/kikuyu_long_s2/s/(be long/(be long)/' forms.csv
    $ python -m lexedata.edit.clean_forms -k '~' -k '*' -s ',' -s ';' -s '/'
    INFO:lexedata:Line 66: Split form 'pɔ́ / ewɔ́' into 2 elements.
    [...]
    INFO:lexedata:Line 588: Split form 'lə̀-náàŋgá * náàŋgá' into 2 elements.
    INFO:lexedata:Line 611: Split form 'lə̀-ɲâdà * ɲâdà' into 2 elements.
    INFO:lexedata:Line 617: Split form 'ndzilá * mà-ndzilá' into 2 elements.
    INFO:lexedata:Line 618: Split form 'mùù-tù * bàà-tà' into 2 elements.
    INFO:lexedata:Line 625: Split form 'mɔ ~ mɔ́ɔ̀nɔ̀' into 2 elements.
    INFO:lexedata:Line 725: Split form 'i-baa ~ i-báːl' into 2 elements.
    INFO:lexedata:Line 739: Split form 'odzá:ng * nzáng' into 2 elements.
    [...]
    $ python -m lexedata.edit.add_segments -q --replace-form
    WARNING:lexedata:In form duala_snake (line 84): Unknown sound ' encountered in nam'a bwaba
    WARNING:lexedata:In form ngombe_all (line 210): Unknown sound ń encountered in ńsò
    WARNING:lexedata:In form ngombe_cold (line 227): Unknown sound ḿ encountered in ḿpyo
    WARNING:lexedata:In form bushoong_dog_s2 (line 363): Unknown sound m̀ encountered in m̀mbwá
    WARNING:lexedata:In form bushoong_neck_s2 (line 411): Unknown sound ʼ encountered in ikɔ́l’l
    WARNING:lexedata:In form bushoong_sleep_v (line 430): Unknown sound ' encountered in abem't
    WARNING:lexedata:In form nzebi_bone (line 564): Unknown sound š encountered in lə̀-šiʃí
    WARNING:lexedata:In form nzebi_give (line 587): Unknown sound š encountered in šɛ
    WARNING:lexedata:In form nzebi_seed (line 627): Unknown sound š encountered in ì-šɛ̂dí
    WARNING:lexedata:In form nzadi_arm (line 655): Unknown sound ` encountered in lwǒ`
    WARNING:lexedata:In form nzadi_rain_s2 (line 750): Unknown sound ɩ́ encountered in mbvɩ́l
    WARNING:lexedata:In form nzadi_tongue (line 779): Unknown sound ɩ́ encountered in lɩlɩ́m
    WARNING:lexedata:In form nzadi_tongue (line 779): Unknown sound ɩ encountered in lɩlɩ́m
    WARNING:lexedata:In form lega_woman_s2 (line 903): Unknown sound o̩ encountered in mo̩-kazi
    WARNING:lexedata:In form kikuyu_tail_s2 (line 1009): Unknown sound ' encountered in gĩ-tong'oe
    WARNING:lexedata:In form swahili_bite (line 1141): Unknown sound ' encountered in ng'ata
    | LanguageID   | Sound   |   Occurrences | Comment                                    |
    |--------------+---------+---------------+--------------------------------------------|
    | Duala        | '       |             1 | unknown sound                              |
    | Ngombe       | ń      |             1 | unknown sound                              |
    | Ngombe       | ḿ      |             1 | unknown sound                              |
    | Bushoong     | m̀      |             1 | unknown sound                              |
    | Bushoong     | ʼ       |             1 | unknown sound                              |
    | Bushoong     | '       |             1 | unknown sound                              |
    | Nzebi        | š      |             3 | unknown sound                              |
    | Nzadi        | ↄ       |             8 | 'ↄ' replaced by 'ɔ' in segments and forms. |
    | Nzadi        | `       |             1 | unknown sound                              |
    | Nzadi        | ɩ́      |             2 | unknown sound                              |
    | Nzadi        | ɩ       |             1 | unknown sound                              |
    | Lega         | o̩      |             1 | unknown sound                              |
    | Kikuyu       | '       |             1 | unknown sound                              |
    | Swahili      | '       |             1 | unknown sound                              |

There are a few unknown symbols left in the data, but most of it is clean IPA now. ::

    $ git commit -am "Clean up forms"
    [...]

Add more tables
---------------

With the segments in place, we can go back to adding the cognate table back in
and proceed to add the cognateset table. ::
    
    $ python -m lexedata.edit.add_cognate_table -q --unique-id concept
    $ python -m lexedata.edit.add_table CognatesetTable
    INFO:lexedata:Found 651 different entries for your new CognatesetTable.
    $ git add cognates.csv cognatesets.csv
    $ git commit -am "Add cognate and cognateset tables"
    [...]

Create a consistent data set
----------------------------
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
    
    $ git commit -am "Update language metadata"
    [...]
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

Now the dataset conforms to cldf::
    
    $ cldf validate Wordlist-metadata.json
    $ git commit -am "Make dataset valid!"
    [...]

Extended extended CLDF compatibility
====================================

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
'MUST', which `allows to ignore the requirement in certain circumstances
<https://datatracker.ietf.org/doc/html/rfc2119#section-3>` and thus ``cldf
validate`` does not enforce it. We do however provide a separate report script
that points out this and other deviations from sensible assumptions. ::

    $ python -m lexedata.report.extended_cldf_validate 2>&1 | head -n 2
    WARNING:lexedata:Table parameters.csv has an unconstrained ID column ID. Consider setting its format to [a-zA-Z0-9_-]+ and/or running `lexedata.edit.simplify_ids`.
    INFO:lexedata:Caching table forms.csv

As that message tells us (I have cut off all the later messages, showing only
the first two lines of output), we can fix this using another tool from the
lexedata toolbox::

    $ python -m lexedata.edit.simplify_ids --table parameters.csv
    INFO:lexedata:Handling table parameters.csv…
    [...]
    $ git commit -am "Regenerate concept IDs"
    [...]

This was however not the only issue with the data. ::

    $ python -m lexedata.report.extended_cldf_validate -q
    WARNING:lexedata:In cognates.csv, row 2: Referenced segments in form resolve to ɓ ɛ́ s ɛ̃, while alignment contains segments .
    WARNING:lexedata:In cognates.csv, row 3: Referenced segments in form resolve to d i a, while alignment contains segments .
    WARNING:lexedata:In cognates.csv, row 4: Referenced segments in form resolve to m a b ú d ú, while alignment contains segments .
    WARNING:lexedata:In cognates.csv, row 5: Referenced segments in form resolve to b w e l é, while alignment contains segments .
    WARNING:lexedata:In cognates.csv, row 6: Referenced segments in form resolve to d i b u m, while alignment contains segments .
    WARNING:lexedata:In cognates.csv, row 7: Referenced segments in form resolve to é n d ɛ̃ n ɛ̀, while alignment contains segments .
    WARNING:lexedata:In cognates.csv, row 8: Referenced segments in form resolve to i n ɔ̌ n, while alignment contains segments .
    [...]

The alignment column of the cognate table is empty, so for no form is there a
match between the segments assigned to a cognate set (the segment slice, applied
to the segments in the FormTable) and the segments occuring in the alignment.
The easy way out here is the alignment script – which is not very clever, but
working on the cognate data in detail is a later step. ::

    $ python -m lexedata.edit.align
    INFO:lexedata:Caching table FormTable
    100%|██████████| 1592/1592 [...]
    INFO:lexedata:Aligning the cognate segments
    100%|██████████| 1585/1585 [...]
    $ git commit -am "Align"
    [...]

Lastly, with accented unicode characters, there are (simlified) two different
conventions: Storing the characters as composed as possible (so è would be a
single character) or as decomposed as possible (storing è as a combining `
character and e). We generally use the composed “NFC” convention, so if you are
in doubt, you can always normalize them to that convention. ::

    $ python -m lexedata.edit.normalize_unicode
    INFO:lexedata:Normalizing forms.csv…
    INFO:lexedata:Normalizing languages.csv…
    INFO:lexedata:Normalizing parameters.csv…
    INFO:lexedata:Normalizing cognates.csv…
    INFO:lexedata:Normalizing cognatesets.csv…
    $ python -m lexedata.report.extended_cldf_validate -q
    $ git commit -am "Get data ready to start editing"
    [...]

We have told the extended validator to be quiet, so no output means it has
nothing to complain about: Our dataset is not only valid CLDF, but also
compatible with the general assumptions of lexedata.

********************
Editing the data set
********************

We are about to start editing. In the process, we may introduce new issues into
the dataset. Therefore it makes sense to mark this current version with a git
tag. If we ever need to return to this version, the tag serves as a memorable
anchor. ::

    $ git tag import_complete

Adding status columns
=====================

While editing datasets, it is often useful to track the status of different
objects. This holds in particular when some non-obvious editing steps are done
automatically. Due to this, lexedata supports status columns. Many scripts fill
the status column of a table they manipulate with a short message. The ``align``
script has already done that for us::

    $ head -n3 cognates.csv
    ID,Form_ID,Cognateset_ID,Segment_Slice,Alignment,Source,Status_Column
    duala_all,duala_all,all_1,1:4,ɓ ɛ́ s ɛ̃ - -,,automatically aligned
    duala_arm,duala_arm,arm_7,1:3,d i a,,automatically aligned

Most scripts do not add a status column if there is none. To make use of this
functionality, we therefore add status columns to all tables. ::

    $ python -m lexedata.edit.add_status_column 
    INFO:lexedata:Tables to have a status column: ['forms.csv', 'cognatesets.csv', 'cognates.csv', 'parameters.csv']
    INFO:lexedata:Table cognates.csv already contains a Status_Column.
    $ git commit -am "Add status columns"
    [...]

Improve Concepts
================

The first items we want to edit are the concepts, and the links between the
forms and the concepts. Currently, our parameter table lists for every concept
only a name and an ID derived from the name. There is also space for a
description, which we have left unfilled.

For many subsequent tasks, it is useful to know whether concepts are related or
not. The `CLICS³ database <https://clics.clld.org/>`_ contains a network of
colexifications: Concepts that are expressed by the same form in vastly
different languages can be assumed to be related. Lexedata comes with a copy of
the CLICS³ network, but in order to use it, we need to map concepts to
`Concepticon <https://concepticon.clld.org>`_, a catalog of concepts found in
different word lists.

Guess Concepticon links
-----------------------

Concepticon comes with some functionality to guess concepticon IDs based on
concept glosses. The concepticon script only takes one gloss language into
account. Lexedata provides a script that can take multiple gloss languages – we
don't have those here, but the lexedata script can also add Concepticon's
normalized glosses and definitions to our parameter table, so we use that script
here. Our “Name” column in the ParameterTable contains English (“en”) glosses,
so pass that information to the script::

    $ python -m lexedata.edit.add_concepticon -q -l Name=en --add-concept-set-names --add-definitions
    OrderedDict([('ID', 'bark'), ('Name', 'bark'), ('Description', None), ('Status_Column', None), ('Concepticon_ID', None)]) 2 [('1204', 3), ('1206', 1)]
    OrderedDict([('ID', 'breast'), ('Name', 'breast'), ('Description', None), ('Status_Column', None), ('Concepticon_ID', None)]) 2 [('1402', 3), ('1592', 1)]
    OrderedDict([('ID', 'burn'), ('Name', 'burn'), ('Description', None), ('Status_Column', None), ('Concepticon_ID', None)]) 2 [('2102', 3), ('141', 2), ('1428', 2), ('3622', 1)]
    OrderedDict([('ID', 'cloud'), ('Name', 'cloud'), ('Description', None), ('Status_Column', None), ('Concepticon_ID', None)]) 2 [('1489', 3), ('448', 1)]
    OrderedDict([('ID', 'cold'), ('Name', 'cold'), ('Description', None), ('Status_Column', None), ('Concepticon_ID', None)]) 2 [('1287', 3), ('102', 1), ('2483', 1), ('2932', 1)]
    [...]
    
The output shows the concepts in our dataset with some ambiguous mappings to concepticon. Now is the time to check andif necessary fix the mappings. ::

    $ cat parameters.csv 
    ID,Name,Description,Status_Column,Concepticon_ID,Concepticon_Gloss,Concepticon_Definition
    all,all,,automatic Concepticon link,98,ALL,The totality of.
    arm,arm,,automatic Concepticon link,1673,ARM,"The upper limb, extending from the shoulder to the wrist and sometimes including the hand."
    [...]
    $ sed -i.bak -s 's/^go_to.*/go_to,go to,,Concepticon link checked,695,GO,To get from one place to another by any means./' parameters.csv
    $ sed -i.bak -s 's/automatic Concepticon link/Concepticon link checked/' parameters.csv

Merging polysemous forms
------------------------

There are a few identical forms in different concepts. Because we have connected
our concepts to Concepticon, and therefore we have access to their CLICS³
network, the homophones report can tell us whether two concepts are connected
and thus likely polysemies of a single word::

    $ python -m lexedata.report.homophones -o homophones.txt
    $ cat homophones.txt
    Ntomba, 'lopoho': Connected:
    	 ntomba_bark (bark)
    	 ntomba_skin (skin)
    Ngombe, 'nɛ́nɛ': Connected:
    	 ngombe_big (big)
    	 ngombe_many (many)
    Bushoong, 'yɛɛn': Connected:
    	 bushoong_go_to (go_to)
    	 bushoong_walk (walk)
    Bushoong, 'dǐin': Connected:
    	 bushoong_name (name)
    	 bushoong_tooth (tooth)
    Nzadi, 'o-tûm': Unconnected:
    	 nzadi_dig (dig)
    	 nzadi_heart_s2 (heart)
    Lega, 'ɛnda': Connected:
    	 lega_go_to (go_to)
    	 lega_walk (walk)
    Kikuyu, 'rĩa': Connected:
    	 kikuyu_eat (eat)
    	 kikuyu_what (what)
    Kikuyu, 'erũ': Unconnected:
    	 kikuyu_new (new)
    	 kikuyu_white (white)
    Swahili, 'jua': Unconnected:
    	 swahili_know (know)
    	 swahili_sun (sun)
    Ha, 'inda': Unconnected:
    	 ha_belly (belly)
    	 ha_louse (louse)
    Ha, 'gwa': Unconnected:
    	 ha_fall (fall)
    	 ha_rain_v (rain_v)
    Fwe, 'wa': Unconnected:
    	 fwe_fall (fall)
    	 fwe_give_s2 (give)
    Fwe, 'ya': Unconnected:
    	 fwe_go_to (go_to)
    	 fwe_new (new)

The output is not as helpful as we might have hoped (that ‘bark’ and ‘skin’ are
connected makes sense, but ‘eat’ and ‘what’ are connected and ‘new’ and ‘white’
disconnected?). We can edit this [1]_ to keep the polysemies ::

    $ cat > polysemies.txt << EOF
    > Ntomba, 'lopoho': Connected:
    > 	 ntomba_bark (bark)
    > 	 ntomba_skin (skin)
    > Ngombe, 'nɛ́nɛ': Connected:
    > 	 ngombe_big (big)
    > 	 ngombe_many (many)
    > Bushoong, 'yɛɛn': Connected:
    > 	 bushoong_go_to (go_to)
    > 	 bushoong_walk (walk)
    > Lega, 'ɛnda': Connected:
    > 	 lega_go_to (go_to)
    > 	 lega_walk (walk)
    > Kikuyu, 'erũ': Unconnected:
    > 	 kikuyu_new (new)
    > 	 kikuyu_white (white)
    > EOF

and feed this file into the ‘homophones merger’, which turns separate forms into
polysemous forms connected to multiple concepts. ::

    $ python -m lexedata.edit.merge_homophones polysemies.txt
    WARNING:lexedata:I had to set a separator for your forms' concepts. I set it to ';'.
    INFO:lexedata:Going through forms and merging
    100%|██████████| 1592/1592 [...]

Improve Cognatesets
===================

Merge cognatesets
-----------------

From merging polysemous forms, which were in different cognate sets, we get
morphemes which are now allocated to two different cognate sets.

nonconcatenative_morphemes.py

These can be used to merge the corresponding cognate sets.

  TODO: The script to merge this kind of indirectly connected cognate sets does
  not exist. What should it do?

Central Concepts
----------------

Singletons
----------

Singletons
----------
Align

****************************************
Computer-assisted historical linguistics
****************************************

Cognate Excel
=============

Edictor
=======

*************
Further steps
*************

Matrix exporter
===============

Phylogenetics
=============

.. rubric:: Footnotes

.. [1] The syntax I used to describe files before does not like indented lines
       in the file, but they are integral to the structure of the polysemies
       list.
