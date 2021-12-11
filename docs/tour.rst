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
    $ cldf validate Wordlist-metadata.json

First, we change the template metadata file to include an actual description of
what most people might understand when we say “metadata”: Authors, provenience,
etc.

    ::

       [model ie_vocabulary]
       model = covarion
       data = ie_cognates.csv

    -- ie_vocabulary.conf

::

    $ ls
