# `lexedata` Manual

  * [1. Introduction](#1-introduction)
    + [1.1 The CLDF format](#11-the-cldf-format)
      - [1.1.1 Languages.csv](#111-languagescsv)
      - [1.1.2 Parameters.csv](#112-parameterscsv)
      - [1.1.3 Forms.csv](#113-formscsv)
      - [1.1.4 Cognatesets.csv](#114-cognatesetscsv)
      - [1.1.5 Cognates.csv](#115-cognatescsv)
      - [1.1.6 sources.bib](#116-sourcesbib)
      - [1.1.7 Wordlist-metadata.json](#117-wordlist-metadatajson)
    + [1.2 Navigation using the command line](#12-navigation-using-the-command-line)
    + [1.3 Working with git](#13-working-with-git)
      - [1.3.1 Basic git commands](#131-basic-git-commands)
    + [1.4 Lexedata commands](#14-lexedata-commands)
    + [1.5 Some terminology](#15-some-terminology)
  * [2. Lexedata installation instructions](#2-lexedata-installation-instructions)
  * [3. Importing data (lexedata.importer)](#3-importing-data-lexedataimporter)
    + [3.1 Importing a lexical dataset to CLDF from excel](#31-importing-a-lexical-dataset-to-cldf-from-excel)
      - [3.1.1 Importing a lexical dataset using the "long" format](#311-importing-a-lexical-dataset-using-the-long-format)
      - [3.1.2 Importing a lexical dataset using the "matrix" format](#312-importing-a-lexical-dataset-using-the-matrix-format)
      - [3.1.3 Importing a lexical dataset using the "interleaved" format](#313-importing-a-lexical-dataset-using-the-interleaved-format)
    + [3.2 Adding a new language/new data to an existing lexical dataset](#32-adding-a-new-languagenew-data-to-an-existing-lexical-dataset)
  * [4. Editing data (lexedata.edit)](#4-editing-data-lexedataedit)
    + [4.1 Linking concepts to concepticon](#41-linking-concepts-to-concepticon)
    + [4.2 Automatic cognate detection](#42-automatic-cognate-detection)
    + [4.3 Adding central concepts to cognate sets](#43-adding-central-concepts-to-cognate-sets)
    + [4.4 Segment forms using CLTS](#44-segment-forms-using-clts)
    + [4.5 How to merge concepts](#45-how-to-merge-concepts)
  * [5. Reporting and checking data integrity (lexedata.report)](#5-reporting-and-checking-data-integrity-lexedatareport)
    + [5.1 CLDF format validation](#51-cldf-format-validation)
    + [5.2 non-concatenative morphology](#52-non-concatenative-morphology)
    + [5.3 potential synonyms and homophones](#53-potential-synonyms-and-homophones)
    + [5.4 Phonemic inventories and transcription errors](#54-phonemic-inventories-and-transcription-errors)
  * [6. Exporting data (lexedata.exporter)](#6-exporting-data-lexedataexporter)
    + [6.1 Cognate Table export-import loop](#61-cognate-table-export-import-loop)
    + [6.2 Edictor export-import loop](#62-edictor-export-import-loop)
    + [6.3 Comparative Wordlist export](#63-comparative-wordlist-export)
    + [6.4 Exporting coded data for phylogenetic analyses (lexedata.exporter.phylogenetics)](#64-exporting-coded-data-for-phylogenetic-analyses-lexedataexporterphylogenetics)
  * [7. How to edit data](#7-how-to-edit-data)
    + [7.1 Editing raw data through GitHub](#71-editing-raw-data-through-github)

## 1. Introduction
Lexedata is a set of tools for managing, editing, and annotating large lexical datasets in CLDF. In order to use lexedata you need to be somewhat familiar with the command line and git. Below we give the basics on the CLDF data format, command line navigation and git that you need to get started, as well as some useful links for more information. Finally we describe how commands are organized in lexedata, and we introduce some terminology we will be using in the manual.

Lexedata is open access software in development. Please report any problems and suggest any improvements you would like to see by [opening an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/creating-an-issue#creating-an-issue-from-a-repository) on the [Lexedata GitHub repository](https://github.com/Anaphory/lexedata/tree/master).

### 1.1 The CLDF format
The CLDF format is designed for sharing and reusing comparative linguistic data. A CLDF lexical dataset consists of a series of .csv files, a metadata .json file describing the structure of each .csv file and their inter-relationships, and a .bib file containing the relevant sources. A typical CLDF lexical dataset consists of the following .csv files: languages.csv, parameters.csv (listing concepts), forms.csv, cognatesets.csv, and cognates.csv. Not all files are necessary: the bare minimum for a valid CLDF dataset is forms.csv. However, lexedata requires a metadata json file for almost every operation.

Each .csv file has to have an ID column. Below, we briefly describe the typical files of a lexical CLDF dataset and how they interact with Lexedata when necessary. For each file, you can find below the necessary columns and typical columns. You can always add any custom columns as needed for your dataset. There is also the possibility to add further .csv files depending on your needs. For more information on the CLDF format, you can refer to https://cldf.clld.org/.

We recommend that you keep all these files in one folder which is versioned with git. You can use Github or Gitlab for this purpose, see section 1.3 below.

#### 1.1.1 languages.csv
The file `languages.csv` contains the different varieties included in your lexical dataset and their metadata. Every row is a variety.
Necessary columns: Language_ID
Typical columns: Language_name


#### 1.1.2 parameters.csv
The `parameters.csv` (sometimes also named `concepts.csv` in datasets with manually created metadata) contains the different concepts (meanings) included in your lexical dataset. Every row is a concept.

 - Necessary columns: Concept_ID
 - Typical columns: Concept_name, Definition, Concepticon_ID

#### 1.1.3 forms.csv
The FormTable, contained in a file usually named `forms.csv`, is the core of a lexical dataset.
A well-structured `forms.csv` on its own, even without accompanying metadata, can already be understood as a lexical dataset by many CLDF-aware applications.
The table contains all the different forms included in your dataset. Every row is a form. To add page numbers for the sources in the cldf format, you should use the format source[page]. You can have different page numbers and page ranges within the square brackets (e.g. `smith2003[45, 48, 52-56]`).

 - Necessary columns: Form_ID, Form, Concept_ID, Language_ID
 - Typical columns: Comment, Segments, Source

#### 1.1.4 cognatesets.csv
Cognatesets.csv contains the cognate sets included in your dataset and their metadata. Every row is a cognate set. Note that, depending on the dataset, cognate set here can either mean cross-concept cognate set (all forms descending from the same protoform), or root-meaning set (all forms descending from the same protoform that have the same meaning). Lexedata is capable of automatically deriving root-meaning sets from cross-concept cognate sets, but the reverse is of course not possible.
Necessary columns: Cognateset_ID
Typical columns: Comment, Source

#### 1.1.5 cognates.csv
Cognates.csv contains all the individual cognate judgements included in the dataset, i.e. it links every form to the cognateset it belongs to. Note that it is possible to have forms belonging to multiple cognate sets (e.g. to account for partial cognacy). 
<!--TO DO: add reference to somewhere, where more complex datasets are explained. 
 NCP: what was the intent of this comment? Should we have a section on partial cognacy?-->
Necessary columns: Cognate_ID, Form_ID, Cognateset_ID
Typical columns: Comment

#### 1.1.6 sources.bib
This is a BibTeX file containing references to all sources used in the dataset. The entries in the Source column of the forms.csv (or any other table) must be identical to a handle (unique code) of a reference in the `sources.bib`.

#### 1.1.7 Wordlist-metadata.json
The Wordlist-metadata.json file contains a detailed description of all the CSV files, their columns and their interrelationships. It is not required file for a CLDF dataset, but it is necessary for the vast majority of operations using lexedata. For simple datasets, lexedata can create automatically a json file (see section XXX). However, for more complex datasets, you would need to provide one yourself.
<!--- TODO: add some support for making a json file--->

For an example of a simple .json file, see XXX. Every change to the structure of the dataset (e.g. insertion or deletion of a column in any file) needs to be reflected in the .json file for the dataset to be a valid cldf dataset.
<!-- TO DO: add a reference to sample files and sample datasets --> 
Below you can see a typical description of a .csv file in the .json file.

![](figures/json.png)

### 1.2 Navigation using the command line
On a MacOS computer you can navigate to a specific folder using the command line on your terminal as follows: 
You can see the directory (folder) you are in at the moment (current directory) within the prompt. In order to go to a directory below (contained in the current directory), type `cd [relative directory path]`, e.g. `cd Documents/arawak/data`. `cd` stands for change directory. Note that directory names are case sensitive and that they can be automatically filled in (if they are unique) by pressing the tab key. 
In order to go to a directory above (the directory containing the current directory), type `cd ..`. Note that you can type any path combining up and down steps. So, if I am in the data directory given as an example above, in order to go to the directory maweti-guarani which is within Documents, I can type `cd ../../maweti-guarani`.
At any point you can see the contents of your current directory by typing `ls`.

### 1.3 Working with git
Git is a version control system. It keeps track of changes so you can easily revert to an earlier version or store a snapshot of your project (e.g. the state of the dataset for a particular article you published). While you could use Lexedata without git, we highly recommend storing your data in a repository (folder) versioned with git.
In this manual we are going to cover some basic commands to get you started. You can find more detailed instructions and more information on how to begin with git [here](https://product.hubspot.com/blog/git-and-github-tutorial-for-beginners) and also in the [tutorials](https://guides.github.com/) by Github. You can also download and use the GitHub Desktop application if you prefer to not use the command line to interact with GitHub. However, you do need to use the command line to interact with Lexedata.

#### 1.3.1 Basic git commands
Below we are going to describe the use of the most basic git commands. We assume a setup with a local git repository (on your computer) and a remote repository (e.g. on GitHub).

`git fetch`: This command "informs" the git on your computer about the status of the remote repository. It does *not* update or change any files in your local repository.

`git status`: This commands gives you a detailed report of the status of your local repository, and also in relation to your remote repository. In the report you can see any changes that you have done to your local repository, and if they are commited or not, as well as any committed changes that have happened in the remote repository in the meantime.

`git pull`: With this command you can update your local repository to be identical to the remote one. This will not work if you have uncommitted changes to protect your work.

`git add [filename]`: This command adds new or modified files to git, or it "stages" the changes to be committed.

`git commit -m "[commit message]"`: After adding (or staging) all the changes that you want to commit, you can use this command to commit the changes to your local repository with an associated commit message. Typically the commit message contains a summary of the changes. This command will *not* update the remote repository.

`git push`: This command will push (or publish) your local commits to the remote repository, which will be updated to reflect these new changes.

To ensure dataset integrity, we recommend running `cldf validate Wordlist-metadata.json` before committing and pushing, so that any cldf errors are caught and corrected (see section [5.1](#51-cldf-format-validation)).

<!--TODO: how do you set up git for the command line in the first place??? Natalia doesn't remember. -->

### 1.4 Lexedata commands

You can access the Lexedata tools through commands in your terminal. Every command has the following general form:
`python -m lexedata.[package_name].[command_name] --[optional argument] [positional argument]`
Elements in brackets above need to be replaced depending on the exact operation you want to perform on your dataset. Also, there could be multiple positional arguments and optional arguments (with only a space as a separator), as well as commands that take only positional or only optional arguments. Positional arguments are not preceded by a hyphen and need to occur in strict order (if there are more than two of them). Optional arguments are always preceded by two hyphens and they can occur in any order after the command. Some optional arguments have a short name of one letter in addition to their regular name and in this case they are preceded by one hyphen (e.g. to access the help of any command you can use the optional argument `--help` or `-h`). Many positional arguments and most optional arguments have default settings. Commands in Lexedata are organized in four packages: lexedata.importer, lexedata.edit, lexedata.report, and lexedata.exporter. (In case you are wondering why they are not called "import" and "export", these words have special status in Python, so they were not available!). If a command name consists of more than one word, the words are separated with an underscore. Optional arguments consisting of more than one word also include underscores.

Probably the most important thing to know before you get started with Lexedata is how to get help. You can access the help of every command by typing `python -m lexedata.[package_name].[command_name] --help`. The help explains how the command is used, what it does and lists all the positional and optional arguments, along with their default values if any.

### 1.5 Some Terminology

Lexedata is CLDF-centric, so ‘export’ is always ‘away from CLDF’ and ‘import’ is always ‘towards CLDF’.

## 2. Lexedata installation instructions

<!-- Is installation any different on other operation systems??? -->

The following instructions are for MacOS computers.

1. In order to install and use Lexedata you need to have Python 3.7 (or newer) installed.

If you are unsure if this is the case, open a terminal window and type `python
--version`. If Python 3.7 (or newer,  is installed you will see the version. If you don't have
any version of Python or it is a version of Python 2, then you need to download
and install Python 3. There are different distributions of Python and most of
them should work. A popular one that we have tested is
[Anaconda](https://www.anaconda.com/products/individual). Once you have
downloaded and installed Anaconda close and open the terminal again and type
`python --version` again. You should see the current version of Python 3 you
just downloaded.

If you are ever stuck with the python prompt, which starts with `>>>`, in
order to exit Python type `quit()`.

3. Install the lexedata package.
In your terminal window type `pip install lexedata`. 
<!---NCP: is this still the case for the new releases? --->
This will install lexedata and all its dependencies on your computer and make it
automatically updatable every time you pull a new version of the Lexedata
repository from GitHub. Now you should be ready to use lexedata!

## 3. Importing data (lexedata.importer)

### 3.1 Importing a lexical dataset to CLDF from excel
Lexedata has different ways of creating a lexical dataset from raw data depending on the format the raw data are in. Currently, three different dataset formats are supported: "long format", "matrix", and "interleaved". The file format in all cases is assumed to be .xlsx. 
The "long format" assumes that every field in CLDF is a different column in your spreadsheet, and that each sheet of your spreadsheet is a different language. In other words, it assumes that you have a wordlist per language. The "matrix" format assumes that your spreadsheet is a comparative wordlist with different languages as different columns. You may have different kinds of information in each cell (e.g. forms and translations), as long as they are machine readable. The matrix importer can also import a separate xls spreadsheet with cognate sets *at the same time* that the forms are imported to a CLDF dataset. The "interleaved" format assumes that you have alternating rows of data and cognate coding. It is similar to the "matrix" format, with the addition that under every row there is an extra row with numerical codes representing cognate classes.

There are multiple types of information that lexedata can extract from excel files. A first distinction is between the content of the cells and the contents of a comment or note associated with the cell. Lexedata reads excel comments and stores them in a dedicated comment field when importing from a matrix and an interleaved format. However, it does not import comments from a long_format dataset (the assumption being that due to the long format, a dedicated column for columns would already exist if desired). Within the cell contents, there could be different types of information as well: e.g. more precise translations, sources, variant forms etc. Automatic separation of these different types of information depends on them being machine readable, i.e. they should be able to be automatically detected, because they are enclosed in different kinds of brackets. The "matrix" format importer script is the most sophisticated and customizable in terms of automatic separation of cell contents.

#### 3.1.1 Importing a lexical dataset using the "long" format
In order to import a lexical dataset in a "long" excel format you need to provide lexedata with a json file describing the CLDF dataset you want to build. 
<!--- TODO: add some chapter of json building--->
The relevant command is:

```
python -m lexedata.importer.excel_long_format [path to excel file] --metadata [path to json file]
```
You can exclude individual sheets from being imported by using the option `--exclude-sheet [sheet name]`.

The long format assumes that each type of information is in a separate column and the content of a cell cannot be separated further. Excel comments (or notes) are not supported with this importer script.

#### 3.1.2 Importing a lexical dataset using the "matrix" format

The matrix format importer is highly customizable, since many different types of information can be included in each cell, apart from the form itself. As long as the cells are machine readable, lexedata can extract most of the information and correctly assign it in different fields of a CLDF dataset. The matrix importer is customized through a special key in the metadata json file. 
<!---TODO: more info is needed about how to set this up---> 

At the same time as the importation of forms, cognate information can be imported to the CLDF dataset from a separate spreadsheet, where every row is a cognate set. The contents of the cells of this second cognatesets spreadsheet are assumed to be easily relatable to the forms (e.g. matching the forms and source). 

#### 3.1.3 Importing a lexical dataset using the "interleaved" format
In the interleaved format, even rows contain forms, while odd rows contain the associated cognate codes. The cognate codes are assumed to be in the same order as the forms and a cognate code is expected for every form (even if this results in a cognate code being present in a cell multiple times). The interleaved importer is the only importing script in lexedata that does not require a json file. However, it also cannot perform any automatic treatment of information within the cells, apart from separation using a customizable separator. For example, if forms in the xlsx file are separated by ; and then some of the forms are followed by parentheses containing translations, each cell is going to be parsed according to the ; and everything in between will be parsed as the form (including the parentheses). You can edit further this dataset to separate the additional kinds of information by editing the forms.csv file that will be created. (see section XXX). 
In order to import a dataset of the "interleaved" format you should use the command
```python -m lexedata.importer.excel_interleaved ``` followed by the name of the excel file containing the dataset. Only a forms.csv file will be created, which contains a Cognateset_ID column with cognate codes. This format is similar to the LingPy format. Note that for any further use of this CLDF dataset with lexedata, you need to create a json file (see sections XXX to create your own json file by hand or automatically respectively).

### 3.2 Adding a new language/new data to an existing lexical dataset


## 4. Editing data (lexedata.edit)

### 4.1 Linking concepts to concepticon
Lexedata can automatically link the concepts of a dataset with concept sets in the Concepticon (https://concepticon.clld.org/). In order to use this functionality, navigate to your depository and type ```python -m lexedata.enrich.guess_concepticon Wordlist-metadata.json```.
Your ParameterTable will now have two new columns: Concepticon ID and Concepticon Name. We recommend that you manually inspect these links for errors. 


### 4.2 Automatic cognate detection

### 4.3 Adding central concepts to cognate sets
```python -m lexedata.enrich.guess_concept_for_cognateset```
```--overwrite``` to overwrite existing central concepts for all cognatesets.

### 4.4 Segment forms using CLTS
In order to align forms to find correspondence sets and for automatic cognate detection, you need to segment the forms. Lexedata uses CLTS to segment the forms. To use this functionality type: ```python -m lexedata.edit.add_segments```. A column "Segments" will be filled in in your forms.csv. The segmenter makes some educated guesses and automatic corrections regarding segments (e.g. obviously wrong placed tiebars for affricates, non-IPA stress symbols, etc). All these corrections are listed in the segmenter's report for you to review. You may choose to apply these corrections to the form column as well.

Optional arguments:

```--metadata [METADATA]```: the metadata file of your dataset

```--overwrite```: segment all forms rather than only unsegmented forms (default behavior)

```--replace-form```: with this option, any automatic corrections are applied not only on the Segments column, but also on the form itself in the #form column.

<!-- Should this section be before the automatic cognate detection? Or when the automatic cognate detection is done it automatically segments as well? Finally, should we add more info about CLTS? Do you like this way of listing stuff? should I do it everywhere?-->

### 4.5 How to merge concepts

## 5. Reporting and checking data integrity (lexedata.report)
### 5.1 CLDF format validation
### 5.2 non-concatenative morphology
### 5.3 potential synonyms and homophones
### 5.4 Phonemic inventories and transcription errors

## 6. Exporting data (lexedata.exporter)
### 6.1 Cognate Table export-import loop

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

1. Validate your dataset using the cldf validate command
It is always a good idea to validate your dataset before and after any edits to make sure that everything is linked as it should in the cldf format.
To perform this test, navigate to your lexical dataset repository and type
```
cldf validate Wordlist-metadata.json
```
Assuming that there are not any errors or warnings you need to take care of, you can proceed to the next step.

2. Export the Cognate Table
Type 
```
python -m lexedata.exporter.cognates [filename]
```
The Cognate Table will be written to an excel file with the specified name.

3. Open and edit the Cognate Table in a spreadsheet editor
(You are, of course, able to upload the cognate excel into Google Sheets, and
download your changes as Excel file, which you then use for the following
re-import step.)

4. Re-import the Cognate Table in lexedata
Once you have edited and/or annotated the Cognate Table, you can update your dataset by re-importing it. Type
```
python -m lexedata.importer.cognates
```

5. Validate your dataset, to make sure that the import went smoothly
Run
```
cldf validate Wordlist-metadata.json`
```
as described in step 1. Hopefully, if you did not see any issues in step 1, you will see none now.

6. Commit and Push (publish) your new version on your dataset repository
You now have an updated version of the repository. If you want to do more
editing of cognate steps, start again at step 1.

### 6.2 Edictor export-import loop
### 6.3 Comparative Wordlist export


### 6.4 Exporting coded data for phylogenetic analyses (lexedata.exporter.phylogenetics)
Lexedata is a powerful tool to prepare linguistic data for phylogenetic analyses. It can be used to export a cldf dataset containing cognate judgements as a coded matrix for phylogenetic analyses to be used by standard phylogenetic software (such as BEAST, MrBayes or revBayes). Different formats are supported, such as nexus, csv, a beast-friendly xml format, as well as a raw alignment format (similar to FASTA format used in bioinformatics). Lexedata also supports different coding methods for phylogenetic analyses: root-meaning sets, cross-meaning cognate sets, and multistate coding. Finally, you can use Lexedata to filter and export a portion of your dataset for phylogenetic analyses, e.g. if some languages or concepts are not fully coded yet, or if you want to exclude specific cognate sets that are not reviewed yet.

## 7. How to edit data
There are two ways to edit data: through the web interface (under
construction) and through editing the .csv files in your corresponding GitHub
repository.

### 7.1 Editing raw data through GitHub
This section describes how to edit raw data through GitHub. By raw data we mean any part of the data that are not cognate set judgements, alignments and related annotations. While it is possible to edit cognate set assignments and annotations this way as well, we recommend that you use the cognate table for this purpose (see section XXX). 
Raw data are contained in three .csv files in the cldf format: `parameters.csv`, `forms.csv`, and `languages.csv`. Note that for small .csv files, instead of following the steps below, you can edit them directly through GitHub's web interface. 

1. pull the dataset repository from GitHub
While in the dataset repository, type `git pull`. 

2. edit the .csv files in a spreadsheet editor
Depending on what you want to edit, you can open any of the .csv files (concepts, forms, and languages) in a spreadsheet editor, edit the corresponding cells and save. 

3. validate your cldf database
Then we recommend to run from the command line, while in the dataset directory:
```cldf validate Wordlist-metadata.json```
This command will perform tests to ensure that your cldf database has no errors. 

4. commit and push your dataset to GitHub
While in the dataset repository, type `git commit` and add a commit message describing your latest changes. Then type  `git push` to publish the latest version to GitHub.

## Command Reference
`edit/add_central_concepts.py
edit/simplify_ids.py
edit/detect_cognates.py
edit/add_judgement_table.py
edit/add_concepticon.py
edit/__init__.py
edit/change_id_column.py
edit/align.py
edit/add_metadata.py
edit/_cognate_code_language.py
edit/add_segments.py
edit/add_singleton_cognatesets.py
edit/unicode_normalize.py
edit/add_status_column.py
edit/_rename_language.py
edit/add_table.py
exporter/__init__.py
exporter/cognates.py
exporter/phylogenetics.py
exporter/edictor.py
importer/__init__.py
importer/cognates.py
importer/excel_interleaved.py
importer/excel_long_format.py
importer/excel_matrix.py
importer/edictor.py
report/homophones.py
report/extended_cldf_validate.py
report/coverage.py
report/__init__.py
report/judgements.py
report/nonconcatenative_morphemes.py
report/filter.py
report/segments_inventories.py
util/__init__.py
util/add_metadata.py
util/fs.py
util/excel.py`
