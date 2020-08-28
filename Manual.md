# `lexedata` Manual

## Lexedata installation instructions

The following instructions are for MacOS computers. Instructions for other operating systems will follow.

#### 1. In order to install and use Lexedata you need to have Python 3 installed.

If you are unsure if this is the case, open a terminal window and type `python
--version`. If Python 3 is installed you will see the version. If you don't have
any version of Python or it is a version of Python 2, then you need to download
and install Python 3. There are different distributions of Python and most of
them should work. A popular one that we have tested is
[Anaconda](https://www.anaconda.com/products/individual). Once you have
downloaded and installed Anaconda close and open the terminal again and type
`python --version` again. You should see the current version of Python 3 you
just downloaded.

If you are ever stuck with the python prompt, which starts with `>>>`, in
order to exit Python type `quit()`.

#### 2. The next step is to clone the Lexedata repository from GitHub on your computer.
You can do this through the command line or through the GitHub desktop
application (follow the instructions/tutorial within the GitHub desktop
applications). If using the command line, in the terminal window, navigate to
the folder where you would like to put the Lexedata folder. Then type `git clone
https://github.com/Anaphory/lexedata`. This should create a folder called
lexedata in the selected location.

#### 3. Install the lexedata package.
In your terminal window type `pip install --user -e ./lexedata`. This will
install lexedata and all its dependencies on your computer and make it
automatically updatable every time you pull a new version of the Lexedata
repository from GitHub. Now you should be ready to use lexedata!

## Importing a lexical dataset to lexedata

### Getting raw data from excel into cldf
Variant one, example from our Arawak dataset
```
python -m lexedata.importer.excelsinglewordlist --exclude-sheet Fields --exclude-sheet Sources --exclude-sheet Languages --add-running-id --concept-property TUS --concept-property TUP Comparative\ Arawakan\ Lexical\ Dataset\ \(active\).xlsx  TUE forms.csv
```
### Adding enriched data
Adding segments, adding links to concepticon

### Automatic cognate coding

## Adding a new language/new data to an existing lexical dataset in lexedata

## How to edit data in lexedata

There are two ways to edit data in lexedata: through the web interface (under
construction) and through editing the .csv files in your corresponding GitHub
repository.

## Cognate Table export-import loop

Lexedata offers the possibility to edit and annotate cognate set (or
root-meaning set) judgements in a spreadsheet format using the spreadsheet
editor of your choice (we have successfully used Google sheets and Microsoft
Excel, but it should work in principle on any spreadsheet editor). In order to
use this functionality, first you need to export your cognate judgements in a
Cognate Table (in xlsx format) and then re-import the modified Cognate Table
back into your lexedata lexical dataset. This process will overwrite previously
existing cognate sets and cognate judgements, as well as any associated comments
(cognate comments and cognate judgement comments).

IMPORTANT: you cannot edit the raw data (forms, translation, form comments etc)
through this process. Instead see XXX how to edit form data in lexedata.

#### 1. Validate your dataset using the cldf validate command
It is always a good idea to validate your dataset before and after any edits to make sure that everything is linked as it should in the cldf format.
To perform this test, navigate to your lexical dataset repository and type
```
python3 -m pycldf validate Wordlist-metadata.json
```
Assuming that there are not any errors or warnings you need to take care of, you can proceed to the next step.

#### 2. Export the Cognate Table
Type 
```
python3 -m lexedata.exporter.cognates
```
The Cognate Table will be written to the excel file `Cognates.xlsx`.

#### 3. Open and edit the Cognate Table in a spreadsheet editor
(You are, of course, able to upload the cognate excel into Google Sheets, and
download your changes as Excel file, which you then use for the following
re-import step.)

#### 4. Re-import the Cognate Table in lexedata
Once you have edited and/or annotated the Cognate Table, you can update your dataset by re-importing it. Type
```
python3 -m lexedata.importer.cognates
```

#### 5. Validate your dataset, to make sure that the import went smoothly
Run
```
python3 -m pycldf validate Wordlist-metadata.json`
```
as described in step 1. Hopefully, if you did not see any issues in step 1, you will see none now.

#### 6. Commit and Push (publish) your new version on your dataset repository
You now have an updated version of the repository. If you want to do more
editing of cognate steps, start again at step 1.
