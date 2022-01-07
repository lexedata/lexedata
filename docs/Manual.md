# `lexedata` Manual

You can access the Lexedata tools through commands in your terminal. Every command has the following general form:

> python -m lexedata.*package*.*command_name* [--*optional-argument* VALUE] [--*switch*] POSITIONAL ARGUMENTS

Elements in italics above need to be replaced depending on the exact command you are using. Elements in capital letters need to be replaced depending on the exact operation you want to perform on your dataset. Optional elements are enclosed in brackets. There could be multiple positional arguments, optional arguments and switches (with only a space as a separator).  Positional arguments are not preceded by a hyphen and need to occur in strict order (if there are more than two of them). Optional arguments and switches are always preceded by two hyphens and they can occur in any order after the command. Optional arguments require a value (often there is a default value), while switches do not. Some optional arguments or switches have a short name of one letter in addition to their regular name and in this case they are preceded by one hyphen (e.g. to access the help of any command you can use the switch `--help` or `-h`). Many positional arguments and most optional arguments have default settings. Commands in Lexedata are organized in four packages: lexedata.importer, lexedata.edit, lexedata.report, and lexedata.exporter. (In case you are wondering why they are not called "import" and "export", these words have special status in Python, so they were not available!). If a command name consists of more than one word, the words are separated by an underscore. However, if optional arguments or switches consist of more than one word, the words are separated by a hyphen. If you need to replace an element in capital letters with a phrase including a space, enclose the whole phrase in quotes (""). 

Probably the most important thing to know before you get started with Lexedata is how to get help. This manual contains all available commands and describes their most common uses but it is not exhaustive as far as optional arguments and switches are concerned. It is highly recommended to first read the help of any new command you are thinking of using. You can access the help of any command by typing `python -m lexedata.*package.command* --help`. The help explains how the command is used, what it does and lists all the positional and optional arguments, along with their default values, if any. If you find the help confusing, or something is missing, do not hesitate to let us know by opening an issue on GitHub.

## Importing data (lexedata.importer)

### Importing a lexical dataset to CLDF from excel
Lexedata has different ways of creating a lexical dataset from raw data depending on the format the raw data are in. Currently, three different dataset formats are supported: "long format", "matrix", and "interleaved". The file format in all cases is assumed to be .xlsx. 
The "long format" assumes that every field in CLDF is a different column in your spreadsheet, and that each sheet of your spreadsheet is a different language. In other words, it assumes that you have a wordlist per language. The "matrix" format assumes that your spreadsheet is a comparative wordlist with different languages as different columns. You may have different kinds of information in each cell (e.g. forms and translations), as long as they are machine readable. The matrix importer can also import a separate xls spreadsheet with cognate sets *at the same time* that the forms are imported to a CLDF dataset. The "interleaved" format assumes that you have alternating rows of data and cognate coding. It is similar to the "matrix" format, with the addition that under every row there is an extra row with numerical codes representing cognate classes.

There are multiple types of information that lexedata can extract from excel files. A first distinction is between the content of the cells and the contents of a comment or note associated with the cell. Lexedata reads excel comments and stores them in a dedicated comment field when importing from a matrix and an interleaved format. However, it does not import comments from a long_format dataset (the assumption being that due to the long format, a dedicated column for columns would already exist if desired). Within the cell contents, there could be different types of information as well: e.g. more precise translations, sources, variant forms etc. Automatic separation of these different types of information depends on them being machine readable, i.e. they should be able to be automatically detected, because they are enclosed in different kinds of brackets. The "matrix" format importer script is the most sophisticated and customizable in terms of automatic separation of cell contents.

#### Importing a lexical dataset using the "long" format
In order to import a lexical dataset in a "long" excel format you need to provide lexedata with a json file describing the CLDF dataset you want to build. 
<!--- TODO: add some chapter of json building--->
The relevant command is:

```
python -m lexedata.importer.excel_long_format [path to excel file] --metadata [path to json file]
```
You can exclude individual sheets from being imported by using the option `--exclude-sheet [sheet name]`.

The long format assumes that each type of information is in a separate column and the content of a cell cannot be separated further in different cells (however, fields including separators are properly recognized provided that you have described them in the json file). Excel comments (or notes) are not supported with this importer script.

#### Importing a lexical dataset using the "matrix" format

The matrix format importer is highly customizable, since many different types of information can be included in each cell, apart from the form itself. As long as the cells are machine readable, lexedata can extract most of the information and correctly assign it in different fields of a CLDF dataset. The matrix importer is customized through a special key in the metadata json file. 
<!---TODO: more info is needed about how to set this up---> 

At the same time as the importation of forms, cognate information can be imported to the CLDF dataset from a separate spreadsheet, where every row is a cognate set. The contents of the cells of this second cognatesets spreadsheet are assumed to be easily relatable to the forms (e.g. matching the forms and source). 

#### Importing a lexical dataset using the "interleaved" format
In the interleaved format, even rows contain forms, while odd rows contain the associated cognate codes. The cognate codes are assumed to be in the same order as the forms and a cognate code is expected for every form (even if this results in a cognate code being present in a cell multiple times). The interleaved importer is the only importing script in lexedata that does not require a json file. However, it also cannot perform any automatic treatment of information within the cells, apart from separation using a customizable separator. For example, if forms in the xlsx file are separated by ; and then some of the forms are followed by parentheses containing translations, each cell is going to be parsed according to the ; and everything in between will be parsed as the form (including the parentheses). You can edit further this dataset to separate the additional kinds of information by editing the forms.csv file that will be created. (see section XXX). 
In order to import a dataset of the "interleaved" format you should use the command
```python -m lexedata.importer.excel_interleaved ``` followed by the name of the excel file containing the dataset. Only a forms.csv file will be created, which contains a Cognateset_ID column with cognate codes. This format is similar to the LingPy format. Note that for any further use of this CLDF dataset with lexedata, you need to create a json file (see sections XXX to create your own json file by hand or automatically respectively).

### Adding a new language/new data to an existing lexical dataset
The importation script using the long format can be used to add new data to an existing dataset, as in the case of adding an new variety or further lexical items for an existing variety (see section [3.1.1] (311-importing-a-lexical-dataset-using-the-long-format)). 

## Editing a CLDF dataset (lexedata.edit)
The "edit" package includes a series of scripts to automate common targeted or batch edits in a lexical dataset. It also included scripts that create links to Concepticon (TODO: add link) and integrate with LingPy (TODO: add link).

### CLDF dataset structure and curation

#### How to add a metadata file (add_metadata)
If your CLDF dataset contains only a FormTable (the bare minimum for a CLDF dataset), you can automatically add a metadata (json) file using the command `python -m lexedata.edit.add_metadata`. Lexedata will try to automatically detect CLDF roles for your columns (such as #form, #languageReference, #parameterReference, #comment, etc) and create a corresponding json file. We recommend that you inspect and adjust manually this json file before you proceed (see section XXX how to read a json file). The add_metadata command can be used also for LingPy output files, in order to obtain a CLDF dataset with metadata.

#### How to add tables to your dataset (add_table)
Once you have a metadata file, you can add tables to your dataset (such as LanguageTable, ParameterTable) automatically. Such tables are required for most lexedata commands. The relevant command is `python -m lexedata.edit.add_table TABLE`. The only table that cannot be added with this script is the CognateTable, which of course requires cognate judgements (see section 4.1.3).

#### How to add a CognateTable (add_cognate_table)
The output of LingPy has cognate judgements as a column within the FormTable, rather than in a separate CognateTable as is the standard in CLDF. This is also the format of a FormTable generated when importing an "interleaved" dataset with Lexeata (see section 3.1.3). In these cases, Lexedata can subsequently create an explicit CognateTable using the command `python -m lexedata.edit.add_cognate_table`. Note that you have to indicate if your cognate judgement IDs are unique within the same concept or are valid across the dataset. In other words, if for every concept you have a cognateset with the code 1, then you need to indicate the option `--unique-id concept`, while if you have cross-concept cognate sets you need to indicate the option `--unique-id dataset`.

#### How to normalize unicode (normalize_unicode)
Linguistic data come with a lot of special characters especially for the forms, but also for language names etc. Many of the input methods used for such datasets result in seemingly identical glyphs, which are not necessarily the same unicode character (and are therefore not considered identical by a computer) . Lexedata can normalize unicode across your dataset with the command `python -m lexedata.edit.normalize_unicode`. You can find more info about what unicode normalization [here] (https://towardsdatascience.com/what-on-earth-is-unicode-normalization-56c005c55ad0).

#### Workflow and tracking aid (add_status_column)
When developing and editing a comparative dataset for historical linguistics, you may need to keep track of operations, such as manual checks, input by collaborators etc. You may also wish to inspect manually some of the automatic operations of lexedata. To facilitate such tasks, you can add a "status column" in any of the CLDF tables using the command `python -m lexedata.edit.add_status_column`. How you use status columns is largely up to you. You may manually keep track of your workflow in this column using specific codewords of your choice. Lexedata scripts that perform automatic operations that are not trivial (such as alignments, automatic cognate set detection) usually leave a message in the status column (which is customizable).  

#### Valid and transparent IDs (simplify_ids)
In a CLDF dataset, all IDs need to be unique and be either numeric or restricted alphanumeric (i.e. containing only leters, numbers and underscores). Lexedata command `python -m lexedata.edit.simplify_ids` verifies that all IDs in the dataset are valid and changes them appropriately if necessary. You can also choose to make your IDs transparent (option `--transparent`) so that you can easily tell what they correspond to. With transparent IDs, instead of a numeric ID, a form will have an ID consisting of the languageID and the parameterID: e.g. the word "main" in French would have the ID stan1290_hand.

#### How to replace or merge IDs (replace_id and replace_id_column)
Sometimes you may need to replace an object's ID (e.g. language ID, concept ID, etc), e.g. if accidentally you have used the same ID twice. Lexedata can replace the id of an object and propagate this change in all tables where it is used as a foreign key (i.e. to link back to that object). The relevant command is ```python -m lexedata.edit.replace_id TABLE ORIGINAL_ID REPLACEMENT_ID```. If you intend to merge two IDs, e.g. if you decide to conflate two concepts because they are not distinct in the languages under study, or two doculects that you want to consider as one. you need to use the optional argument ```--merge```. Keep in mind that lexedata cannot automatically merge two or more rows in the table in question, so if for example you merged two Language IDs, then you will have two rows in languages.csv with identical IDs. This will cause a warning if you try to validate your dataset (see section [5.1] (#51-cldf-format-validation). If you want to completely merge the rows, you need to do this by opening the corresponding csv in a spreadsheet or text editor (see section [7] (#7-how-to-edit-raw-data). 

In case you want to replace an entire ID column of a table, then you need to add the new intended ID column to the table and use the command ```python -m lexedata.edit.replace_id_column TABLE REPLACEMENT```.


### Operations on FormTable

src/lexedata//edit/merge_homophones.py

#### Segment forms (add_segments)
In order to align forms to find correspondence sets and for automatic cognate detection, you need to segment the forms included in your dataset. Lexedata can do this automatically using CLTS (TODO: add link). To use this functionality type: ```python -m lexedata.edit.add_segments TRANCRIPTION_COLUMN```, where transcription column refers to the column that contains the forms to be segmented (the #form column by default). A column "Segments" will be added to your FormTable. The segmenter makes some educated guesses and automatic corrections regarding segments (e.g. obviously wrong placed tiebars for affricates, non-IPA stress symbols, etc). All these corrections are listed in the segmenter's report for you to review. You may choose to apply these corrections to the form column as well, using the switch `--replace_form`.


### Operations on ParameterTable (concepts)

#### Linking concepts to Concepticon (add_concepticon)
Lexedata can automatically link the concepts present in a dataset with concept sets in the Concepticon (https://concepticon.clld.org/). The relevant command is ```python -m lexedata.edit.add_concepticon```.
Your ParameterTable will now have a new column: Concepticon ID, with the corresponding ID of a concept set in Concepticon. We recommend that you manually inspect these links for errors. In order to facilitate this task, you can also add columns for the concept set name (`--add_concept_set_name`) and the concepticon definition (`--add_definitions`). Finally, if your ParameterTable contains a Status Column (see section [4.2.5]), any links to the Concepticon will be tagged as automatic, or you can define a custom message using `--status_update "STATUS UPDATE"`.

### Operations on CognateTable (judgements) and CognatesetTable

### Automatic cognate detection (detect_cognates)
src/lexedata//edit/align.py

### Adding central concepts to cognate sets (add_central_concepts)
```python -m lexedata.enrich.guess_concept_for_cognateset```
```--overwrite``` to overwrite existing central concepts for all cognatesets.

src/lexedata//edit/add_singleton_cognatesets.py



## Reporting and checking data integrity (lexedata.report)

(cldf-format-validation)=
### CLDF format validation
### non-concatenative morphology
### potential synonyms and homophones
### Phonemic inventories and transcription errors

## Exporting data (lexedata.exporter)
### Cognate Table export-import loop

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

### Edictor export-import loop
### Comparative Wordlist export


### Exporting coded data for phylogenetic analyses (lexedata.exporter.phylogenetics)
Lexedata is a powerful tool to prepare linguistic data for phylogenetic analyses. It can be used to export a cldf dataset containing cognate judgements as a coded matrix for phylogenetic analyses to be used by standard phylogenetic software (such as BEAST, MrBayes or revBayes). Different formats are supported, such as nexus, csv, a beast-friendly xml format, as well as a raw alignment format (similar to FASTA format used in bioinformatics). Lexedata also supports different coding methods for phylogenetic analyses: root-meaning sets, cross-meaning cognate sets, and multistate coding. Finally, you can use Lexedata to filter and export a portion of your dataset for phylogenetic analyses, e.g. if some languages or concepts are not fully coded yet, or if you want to exclude specific cognate sets that are not reviewed yet.

## How to edit raw data
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
