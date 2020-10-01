# `lexedata` Manual

## 1. Introduction

Lexedata is a set of tools for managing, editing, and annotating large lexical datasets. In order to use lexedata you need to be somewhat familiar with command line and git. Below we give the basics you need to get started. TODO: maybe add a couple of links of online resources?

### 1.1 Navigation using the command line
On a MacOS computer your can navigate to a specific folder using the command line on your terminal as follows: 
You can see the directory (folder) you are in at the moment (current directory) within the prompt. In order to go to a directory below (contained in the current directory), type `cd [relative directory path]`, e.g. `cd Documents/arawak/data`. `cd` stands for change directory. Note that directory names are case sensitive and that they can be automatically filled in (if they are unique) by pressing the tab key. 
In order to go to a directory above (the directory containing the current directory), type `cd ..`. Note that you can type any path combining up and down steps. So, if I am in the data directory given as an example above, in order to go to the directory maweti-guarani which is within Documents, I can type `cd ../../maweti-guarani`.
At any point you can see the contents of your current directory by typing `ls`. 

### 1.2 Basic git commands (HELP GEREON!)
You can use the following git commands in your terminal or you can use the GitHub Desktop application. TODO: how do you set up git for the command line in the first place???
In order to get the latest version of a repository, navigate to the corresponding folder and type `git pull`. If the version on GitHub is different from the one on your computer, it will be updated to match the version on GitHub. If you have made changes on your local version that are not yet pushed (published) on GitHub you will get a warning and you will have a chance to do it. (@Gereon, is this true???)
In order to push your local version to GitHub, so it is updated, you need to first commit and then push your changes. Type `git commit` while in the repository you have modified and you will be prompted to add a commit message describing your latest changes. Then type `git push` and your local version will become the current version on GitHub (assuming that there are no conflicts to resolve). For lexical data repositories we recommend running `cldf validate Wordlist-metadata.json` before commiting and pushing, so that any cldf errors are caught and corrected.

## 2. Lexedata installation instructions

The following instructions are for MacOS computers. TODO: write instructions for windows and linux

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
In your terminal window type `pip install -e ./lexedata`. This will
install lexedata and all its dependencies on your computer and make it
automatically updatable every time you pull a new version of the Lexedata
repository from GitHub. Now you should be ready to use lexedata!

## 3. Importing a lexical dataset to lexedata from excel
Lexedata has two ways of creating a lexical dataset from raw data depending on the format the raw data are in ("long" or "matrix"). 
The "long" format assumes that every field in CLDF is a different column in your spreadsheet, and that each sheet of your spreadsheet is a different language. In other words, it assumes that you have a wordlist per language. The "matrix" format assumes that your spreadsheet is a comparative wordlist with different languages as different columns. You may have different kind of information in each cell (e.g. forms and translations), as long as they are machine readable.

### 3.1 Importing a lexical dataset in lexedata using the "long" format
In order to import a lexical dataset in a "long" excel format you use the following command.

```
python -m lexedata.importer.excelsinglewordlist --add-running-id <filename.xlsx>  <concept column name>  forms.csv
```
You can exclude individual sheets from being imported by using the option `--exclude-sheet <sheet name>`. @Gereon I am not sure I understand the rest of the command. I think that --concept-property TUS is so that this column is added to the concept table, instead of being treated as another language. 

### 3.2 Importing a lexical dataset in lexedata using the "matrix" format




### 3.2 Adding enriched data
Adding segments, adding links to concepticon

### 3.3 Automatic cognate detection

## 4. Adding a new language/new data to an existing lexical dataset in lexedata

## 5. How to edit raw data in lexedata

There are two ways to edit data in lexedata: through the web interface (under
construction) and through editing the .csv files in your corresponding GitHub
repository.

### 5.1 Editing raw data through GitHub
This section describes how to edit raw data through GitHub. By raw data we mean any part of the data that are not cognate set judgements, alignments and related annotations. While it is possible to edit cognate set assignments and annotations this way as well, we recommend that you use the cognate table for this purpose (see section XXX). 
Raw data are contained in three .csv files in the cldf format: concepts.csv, forms.csv, and languages.csv. Note that for small .csv files, instead of following the steps below, you can edit them directly through GitHub's web interface. 

#### 1. pull the dataset repository from GitHub
While in the dataset repository, type `git pull`. 

#### 2. edit the .csv files in a spreadsheet editor
Depending on what you want to edit, you can open any of the .csv files (concepts, forms, and languages) in a spreadsheet editor, edit the corresponding cells and save. 

#### 3. validate your cldf database
Then we recommend to run from the command line, while in the dataset directory:
```cldf validate Wordlist-metadata.json```
This command will perform tests to ensure that your cldf database has no errors. 

#### 4. commit and push your dataset to GitHub
While in the dataset repository, type `git commit` and add a commit message describing your latest changes. Then type  `git push` to publish the latest version to GitHub.


## 6. Cognate Table export-import loop

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
through this process. Instead see XXX how to edit raw data in lexedata.

#### 1. Validate your dataset using the cldf validate command
It is always a good idea to validate your dataset before and after any edits to make sure that everything is linked as it should in the cldf format.
To perform this test, navigate to your lexical dataset repository and type
```
cldf validate Wordlist-metadata.json
```
Assuming that there are not any errors or warnings you need to take care of, you can proceed to the next step.

#### 2. Export the Cognate Table
Type 
```
python -m lexedata.exporter.cognates
```
The Cognate Table will be written to the excel file `Cognates.xlsx`.

#### 3. Open and edit the Cognate Table in a spreadsheet editor
(You are, of course, able to upload the cognate excel into Google Sheets, and
download your changes as Excel file, which you then use for the following
re-import step.)

#### 4. Re-import the Cognate Table in lexedata
Once you have edited and/or annotated the Cognate Table, you can update your dataset by re-importing it. Type
```
python -m lexedata.importer.cognates
```

#### 5. Validate your dataset, to make sure that the import went smoothly
Run
```
cldf validate Wordlist-metadata.json`
```
as described in step 1. Hopefully, if you did not see any issues in step 1, you will see none now.

#### 6. Commit and Push (publish) your new version on your dataset repository
You now have an updated version of the repository. If you want to do more
editing of cognate steps, start again at step 1.
