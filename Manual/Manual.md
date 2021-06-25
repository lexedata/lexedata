# `lexedata` Manual

## 1. Introduction
Lexedata is a set of tools for managing, editing, and annotating large lexical datasets in CLDF. In order to use lexedata you need to be somewhat familiar with the command line and git. Below we give the basics you need to get started, as well as some useful links for more information.

### 1.1 The CLDF format
The CLDF format is designed for sharing and reusing comparative linguistic data. A CLDF lexical dataset consists of a series of .csv files, a .json file describing the structure of each .csv file and their inter-relationships, and a .bib file containing the relevant sources. A typical CLDF lexical dataset consists of the following .csv files: languages.csv, concepts.csv, forms.csv, cognatesets.csv, and cognates.csv. However, not all files are necessary: the bare minimum is forms.csv.
Each .csv file has to have an ID column. Below, we briefly describe the typical files of a lexical CLDF dataset and how they interact with Lexedata when necessary. For each file, you can find below the necessary columns and typical columns. You can always add any custom columns as needed for your dataset. There is the possibility to add further columns and even .csv files depending on your needs. For more information on the CLDF format, you can refer to https://cldf.clld.org/.

We recommend that you keep all these files in one folder which is versioned with git. You can use Github or Gitlab for this purpose, see section 1.3 below.

#### 1.1.1 Languages.csv
Languages.csv contains the different varieties included in your lexical dataset and their metadata. Every row is a variety.
Necessary columns: Language_ID
Typical columns: Language_name


#### 1.1.2 Concepts.csv
Concepts.csv contains the different concepts (meanings) included in your lexical dataset. Every row is a concept.
Necessary columns: Concept_ID
Typical columns: Concept_name, Definition, Concepticon_ID

#### 1.1.3 Forms.csv
Forms.csv contains all the different forms included in your dataset. Every row is a form. To add page numbers for the sources in the cldf format, you should use the format source[page]. You can have different page numbers and page ranges within the square brackets (e.g. smith2003[45, 48, 52-56]).
Necessary columns: Form_ID, Form, Concept_ID, Language_ID, Source
Typical columns: Comment, Segments

#### 1.1.4 Cognatesets.csv
Cognatesets.csv contains the cognate sets included in your dataset and their metadata. Every row is a cognate set. Note that, depending on the dataset, cognate set here can either mean cross-concept cognate set (all forms descending from the same protoform), or root-meaning set (all forms descending from the same protoform that have the same meaning). Lexedata is capable of automatically deriving root-meaning sets from cross-concept cognate sets, but the reverse is of course not possible.
Necessary columns: Cognateset_ID
Typical columns: Comment, Source

#### 1.1.5 Cognates.csv
Cognates.csv contains all the individual cognate judgements included in the dataset, i.e. it links every form to the cognateset it belongs to. Note that it is possible to have forms belonging to multiple cognate sets (e.g. to account for partial cognacy). 
<!--TO DO: add reference to somewhere, where more complex datasets are explained -->
Necessary columns: Cognate_ID, Form_ID, Cognateset_ID
Typical columns: Comment

#### 1.1.6 sources.bib
This is a typical .bib file containing references to all sources used in the dataset. The handle (unique code) of each reference should be identical to the entry in the Source column of the forms.csv.

#### 1.1.7 Wordlist-metadata.json
The Wordlist-metadata.json file contains a detailed description of all the .csv files, their columns and their interrelationships. For an example of a simple .json file, see XXX. Every change to the structure of the dataset (e.g. insertion or deletion of a column in any file) needs to be reflected in the .json file for the dataset to be a valid cldf dataset.
<!-- TO DO: add a reference to sample files and sample datasets --> 
Below you can see a typical description of a .csv file in the .json file.

![](https://github.com/Anaphory/lexedata/blob/nataliacp-patch-1/Manual/figures/json.png)

### 1.2 Navigation using the command line
On a MacOS computer you can navigate to a specific folder using the command line on your terminal as follows: 
You can see the directory (folder) you are in at the moment (current directory) within the prompt. In order to go to a directory below (contained in the current directory), type `cd [relative directory path]`, e.g. `cd Documents/arawak/data`. `cd` stands for change directory. Note that directory names are case sensitive and that they can be automatically filled in (if they are unique) by pressing the tab key. 
In order to go to a directory above (the directory containing the current directory), type `cd ..`. Note that you can type any path combining up and down steps. So, if I am in the data directory given as an example above, in order to go to the directory maweti-guarani which is within Documents, I can type `cd ../../maweti-guarani`.
At any point you can see the contents of your current directory by typing `ls`. 

<!-- Is navigation any different in different operating systems??? -->

### 1.3 Working with git
Git is a version control system. It keeps track of changes so you can easily revert to an earlier version or store a snapshot of your project (e.g. the state of the dataset for a particular article you published). While you could use Lexedata without git, we highly recommend storing your data in a repository (folder) versioned with git.
In this manual we are going to cover some basic commands to get you started. You can find more detailed instructions and more information on how to begin with git [here](https://product.hubspot.com/blog/git-and-github-tutorial-for-beginners) and also in the [tutorials](https://guides.github.com/) by Github. You can also download and use the GitHub Desktop application if you prefer to not use the command line to interact with GitHub. However, you do need to use the command line with Lexedata.

#### 1.3.1 How to set up git on your computer
<!--- Natalia: if somebody follows the tutorials say on github, like this one https://guides.github.com/introduction/git-handbook/, do they need to do something special to get git running on their computer? -->

#### 1.3.2 Basic git commands
Below we are going to describe the use of the most basic git commands. We assume a setup with a local git repository (on your computer) and a remote repository (e.g. on GitHub).

`git fetch`: This command "informs" the git on your computer about the status of the remote repository. It does *not* update or change any files in your local repository.

`git status`: This commands gives you a detailed report of the status of your local repository, and also in relation to your remote repository. In the report you can see any changes that you have done to your local repository, and if they are commited or not, as well as any committed changes that have happened in the remote repository in the meantime.

`git pull`: With this command you can update your local repository to be identical to the remote one. This will not work if you have uncommitted changes to protect your work.

`git add [filename]`: This command adds new or modified files to git, or it "stages" the changes to be committed.

`git commit -m "[commit message]"`: After adding (or staging) all the changes that you want to commit, you can use this command to commit the changes to your local repository with an associated commit message. Typically the commit message contains a summary of the changes. This command will *not* update the remote repository.

`git push`: This command will push (or publish) your local commits to the remote repository, which will be updated to reflect these new changes.

To ensure dataset integrity, we recommend running `cldf validate Wordlist-metadata.json` before committing and pushing, so that any cldf errors are caught and corrected (see section [5.1](#5.1-cldf-format-validation)).

<!--TODO: how do you set up git for the command line in the first place??? Natalia doesn't remember. -->

### 1.4 Some terminology
Lexedata is CLDF-centric, so ‘Export’ is always ‘away from CLDF’ and ‘import’ is always ‘towards CLDF’.

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
In your terminal window type `pip lexedata`. This will
install lexedata and all its dependencies on your computer and make it
automatically updatable every time you pull a new version of the Lexedata
repository from GitHub. Now you should be ready to use lexedata!

## 3. Importing data (lexedata.importer)

### 3.1 Importing a lexical dataset to CLDF from excel
Lexedata has different ways of creating a lexical dataset from raw data depending on the format the raw data are in ("long format", "matrix", "interleaved"). 
The "long format" assumes that every field in CLDF is a different column in your spreadsheet, and that each sheet of your spreadsheet is a different language. In other words, it assumes that you have a wordlist per language. The "matrix" format assumes that your spreadsheet is a comparative wordlist with different languages as different columns. You may have different kinds of information in each cell (e.g. forms and translations), as long as they are machine readable. The "interleaved" format assumes that you have alternating rows of data and cognate coding. It is similar to the "matrix" format, with the addition that under every row there is an extra row with numerical codes representing cognate classes.

#### 3.1.1 Importing a lexical dataset using the "long" format
In order to import a lexical dataset in a "long" excel format you use the following command.

```
python -m lexedata.importer.excelsinglewordlist --add-running-id <filename.xlsx>  <concept column name>  forms.csv
```
You can exclude individual sheets from being imported by using the option `--exclude-sheet <sheet name>`. @Gereon I am not sure I understand the rest of the command. I think that --concept-property TUS is so that this column is added to the concept table, instead of being treated as another language. 

#### 3.1.2 Importing a lexical dataset using the "matrix" format

#### 3.1.3 Importing a lexical dataset using the "interleaved" format

### 3.2 Adding a new language/new data to an existing lexical dataset


## 4. Editing data (lexedata.edit)

### 4.1 Linking concepts to concepticon
Lexedata can automatically link the concepts of a dataset with concept sets in the Concepticon (https://concepticon.clld.org/). In order to use this functionality, navigate to your depository and type ```python -m lexedata.enrich.guess_concepticon Wordlist-metadata.json```.
Your concepts.csv will now have two new columns: Concepticon ID and Concepticon Name. We recommend that you manually inspect these links for errors. 


### 4.2 Automatic cognate detection

### 4.3 Adding central concepts to cognate sets
```python -m lexedata.enrich.guess_concept_for_cognateset```
```--overwrite``` to overwrite existing central concepts for all cognatesets.

### 4.4 Segment forms using CLTS
In order to align forms to find correspondence sets and for automatic cognate detection, you need to segment the forms. Lexedata uses CLTS to segment the forms. To use this functionality type: ```python -m lexedata.enrich.segment_using_clts```. A column "Segments" will be filled in in your forms.csv. The segmenter makes some educated guesses and automatic corrections regarding segments (e.g. obviously wrong placed tiebars for affricates, non-IPA stress symbols, etc). All these corrections are listed in the segmenter's report for you to review.

Optional arguments:

```--metadata [METADATA]```: the metadata file of your dataset

```--overwrite```: segment all forms rather than only segment unsegmented forms (default behavior)

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


## 7. How to edit data
There are two ways to edit data: through the web interface (under
construction) and through editing the .csv files in your corresponding GitHub
repository.

### 8.1 Editing raw data through GitHub
This section describes how to edit raw data through GitHub. By raw data we mean any part of the data that are not cognate set judgements, alignments and related annotations. While it is possible to edit cognate set assignments and annotations this way as well, we recommend that you use the cognate table for this purpose (see section XXX). 
Raw data are contained in three .csv files in the cldf format: concepts.csv, forms.csv, and languages.csv. Note that for small .csv files, instead of following the steps below, you can edit them directly through GitHub's web interface. 

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

