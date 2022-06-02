# `lexedata` Manual

## lexedata commands

You can access the Lexedata tools through commands in your terminal. Every command has the following general form:

> python -m lexedata.*package*.*command_name* [-\\\-*optional-argument* VALUE] [-\\\-*switch*] POSITIONAL ARGUMENTS

Elements in italics above need to be replaced depending on the exact command you are using. Elements in capital letters need to be replaced depending on the exact operation you want to perform on your dataset. Optional elements are enclosed in brackets. There could be multiple positional arguments, optional arguments and switches (with only a space as a separator).  Positional arguments are not preceded by a hyphen and need to occur in strict order (if there are more than two of them). Optional arguments and switches are always preceded by two hyphens and they can occur in any order after the command. Optional arguments require a value (often there is a default value), while switches do not. Some optional arguments or switches have a short name of one letter in addition to their regular name and in this case they are preceded by one hyphen (e.g. to access the help of any command you can use the switch `--help` or `-h`). Many positional arguments and most optional arguments have default settings.

In order to maintain the integrity of the CLDF format, which is a relational database, lexedata scripts often have to operate on multiple files. It is therefore common that a lexedata command has as an optional argument the metadata file (defaulting to the Wordlist-metadata.json file of the current directory). Thus, the script operates on as many files of the directory containing the CLDF dataset as necessary for the operation at hand. For more information on the CLDF format and its files, see [here](https://github.com/Anaphory/lexedata/blob/natalia-review/docs/cldf.md).

Commands in Lexedata are organized in four packages: [lexedata.importer](#importing-data-lexedata-importer) [^1], [lexedata.edit](#editing-a-cldf-dataset-lexedata-edit), [lexedata.report](#reporting-and-checking-data-integrity-lexedata-report), and [lexedata.exporter](#exporting-data-lexedata-exporter) [^1]. If a command name consists of more than one word, the words are separated by an underscore [^1]. However, if optional arguments or switches consist of more than one word, the words are separated by a hyphen. If you need to replace an element in capital letters with a phrase including a space, enclose the whole phrase in quotes (`"MORE THAN ONE WORD"`). 

[^1]: In case you are wondering why the packages are called **importer** and **exporter**, not import and export: The word `import` has special status in Python, so it was not available as name of a package! The hyphen `-` is used as subtraction symbol in Python, so it also may not be part of a name.

Probably the most important thing to know before you get started with Lexedata is how to get help. This manual contains all available commands and describes their most common uses but it is not exhaustive as far as optional arguments and switches are concerned. It is highly recommended to first read the help of any new command you are thinking of using. You can access the help of any command by typing

> python -m lexedata.*package*.*command_name* -\\\-help

The help explains how the command is used, what it does and lists all the positional and optional arguments, along with their default values, if any. You can export to file the output of many of the scripts in order to use it later. In order to output to file rather than the terminal, add `> FILENAME` after the command for reports, and `2> FILENAME` for lists of errors and/or warnings.

If you find the help confusing, something is missing, or does not work as expected, do not hesitate to let us know by [opening an issue on GitHub](https://github.com/Anaphory/lexedata/issues/new/choose).

## Importing data (lexedata.importer)

### Importing a lexical dataset to CLDF from excel
Lexedata has different ways of creating a lexical dataset from raw data depending on the format the raw data are in. Currently, three different dataset formats are supported: "long format", "matrix", and "interleaved". The file format in all cases is assumed to be .xlsx. 
The "long format" assumes that every field in CLDF is a different column in your spreadsheet, and that each sheet of your spreadsheet is a different language. In other words, it assumes that you have a wordlist per language. The "matrix" format assumes that your spreadsheet is a comparative wordlist with different languages as different columns. You may have different kinds of information in each cell (e.g. forms and translations), as long as they are machine readable. The matrix importer can also import a separate xls spreadsheet with cognate sets *at the same time* that the forms are imported to a CLDF dataset. The "interleaved" format assumes that you have alternating rows of data and cognate coding. It is similar to the "matrix" format, with the addition that under every row there is an extra row with numerical codes representing cognate classes.

There are multiple types of information that lexedata can extract from excel files. A first distinction is between the content of the cells and the contents of a comment or note associated with the cell. Lexedata reads excel comments and stores them in a dedicated comment field when importing from a matrix format. However, it does not import comments from an interleaved or long-format dataset. Within the cell contents, there could be different types of information as well: e.g. more precise translations, sources, variant forms etc. Automatic separation of these different types of information depends on them being machine readable, i.e. they should be able to be automatically detected, because they are enclosed in different kinds of brackets. The "matrix" format importer script is the most sophisticated and customizable in terms of automatic separation of cell contents.

#### Importing a lexical dataset using the "long" format
In order to import a lexical dataset in a "long" excel format you need to provide lexedata with a json file describing the CLDF dataset you want to build (see [how to add a metadata file](#how-to-add-a-metadata-file-add_metadata)).
The relevant command is:

```
python -m lexedata.importer.excel_long_format EXCEL
```
You can exclude individual sheets from being imported by using the option `--exclude-sheet SHEET`. The script can ignore missing or superfluous columns in case your excel file does not match exactly the description in the metadata file (see command help for more information).


The long format assumes that each type of information is in a separate column and the content of a cell cannot be separated further in different cells (however, fields including separators are properly recognized provided that you have described them in the json file). Excel comments (or notes) are not supported with this importer script and they will be ignored.

#### Importing a lexical dataset using the "matrix" format

The matrix format importer is highly customizable, since many different types of information can be included in each cell, apart from the form itself. As long as the cells are machine readable, lexedata can extract most of the information and correctly assign it in different fields of a CLDF dataset. The matrix importer is customized through a special key in the metadata (json) file. At the same time as the importation of forms, cognate information can be imported to the CLDF dataset from a separate spreadsheet, where every row is a cognate set. The contents of the cells of this second cognatesets spreadsheet are assumed to be easily relatable to the forms (e.g. matching the forms and source). 

For an example of the special key in the metadata file, see the [smallmawetiguarani dataset](/test/data/cldf/smallmawetiguarani). You can customize the two cell parsers (CellParser and CognateCellParser), as well as the conditions for a matching form between the two spreadsheets (check_for_match). 

In order to import only a comparative wordlist file (without cognatesets), type
```
python -m lexedata.importer.excel_matrix EXCEL
```
If you want to import cognate sets from a separate spreadsheet, you can use the optional argument `--cogsets COGSET_EXCEL`. 

#### Importing a lexical dataset using the "interleaved" format
In the interleaved format, even rows contain forms, while odd rows contain the associated cognate codes. The cognate codes are assumed to be in the same order as the forms and a cognate code is expected for every form (even if this results in a cognate code being present in a cell multiple times). In case your excel file contains question marks to indicate missing data, the importing script will ignore them. The interleaved importer is the only importing script in lexedata that does not require a metadata (.json) file. However, it also cannot perform any automatic treatment of information within the cells, apart from basic separation (using commas and semi-colons as separators). For example, if forms in the xlsx file are separated by ; and then some of the forms are followed by parentheses containing translations, each cell is going to be parsed according to the ; and everything in between will be parsed as the form (including the parentheses). You can edit further this dataset to separate the additional kinds of information by editing the forms.csv file that will be created. Note that any excel comments present in your file will be ignored. The resulting forms.csv file contains an empty comment field by default.
In order to import a dataset of the "interleaved" format you should use the command
```
python -m lexedata.importer.excel_interleaved FILENAME.xlxs
```
where `FILENAME.xlsx` should be replaced with the name of the excel file containing the dataset. Only a `forms.csv` will be created, which contains a `Cognateset_ID` column with the cognate codes. This format is similar to the LingPy format. Note that for any further use of this CLDF dataset with lexedata, you need to [add a metadata file](#how-to-add-a-metadata-file-add_metadata).

### Adding a new language/new data to an existing lexical dataset
The importation script using the long format can be used to add new data to an existing dataset, as in the case of adding an new variety or further lexical items for an existing variety (see [importing a lexical dataset using the "long" format](#importing-a-lexical-dataset-using-the-long-format)). 


## Editing a CLDF dataset (lexedata.edit)
The "edit" package includes a series of scripts to automate common targeted or batch edits in a lexical dataset. It also includes scripts that create links to [Concepticon(http://concepticon.clld.org) and integrate with [LingPy](http://lingpy.org).

If you need to do editing of raw data in your dataset (such as a transcription, translation, form comment etc), you need to do this manually. For `parameters.csv`, `forms.csv`, and `languages.csv`, you need to open the file in question in a spreadsheet editor, edit it, and save it again in the .csv format. For `cognates.csv` and `cognatesets.csv`, we recommend that you use the Cognate Table export (see [export a Cognate Table](#export-a-cognate-table)). 
Whenever editing a cldf dataset, it is always a good idea to validate the dataset before and after (see [CLDF validate](#cldf-validate)) to make sure that everything went smoothly.

### CLDF dataset structure and curation

#### How to add a metadata file (add_metadata)
If your CLDF dataset contains only a FormTable (the bare minimum for a CLDF dataset), you can automatically add a metadata (json) file using the command 
```
python -m lexedata.edit.add_metadata
```
Lexedata will try to automatically detect CLDF roles for your columns (such as #form, #languageReference, #parameterReference, #comment, etc) and create a corresponding json file. We recommend that you inspect and manually adjust this json file before you proceed (see [the metadata file](/docs/cldf.md#the-metadata-file)). You can also use this command to obtain a starting metadata file for a new dataset. In this case, you can start from an empty FormTable that contains the columns you would like to include. The add_metadata command can be used also for LingPy output files, in order to obtain a CLDF dataset with metadata.

#### How to add tables to your dataset (add_table)
Once you have a metadata file, you can add tables to your dataset (such as LanguageTable, ParameterTable) automatically. Such tables are required for most lexedata commands. The relevant command is 
```
python -m lexedata.edit.add_table TABLE
```
The only table that cannot be added with this script is the CognateTable, which of course requires cognate judgements (see [how to add a CognateTable](#how-to-add-a-cognatetable-add_cognate_table).

#### How to add a CognateTable (add_cognate_table)
The output of LingPy has cognate judgements as a column within the FormTable, rather than in a separate CognateTable as is the standard in CLDF. This is also the format of a FormTable generated when importing an "interleaved" dataset with Lexedata (see [importing a lexical dataset using the "interleaved" format](#importing-a-lexical-dataset-using-the-interleaved-format)). In these cases, Lexedata can subsequently create an explicit CognateTable using the command 
```
python -m lexedata.edit.add_cognate_table
```
Note that you have to indicate if your cognate judgement IDs are unique within the same concept or are valid across the dataset. In other words, if for every concept you have a cognateset with the code 1, then you need to indicate the option `--unique-id concept`, while if you have cross-concept cognate sets you need to indicate the option `--unique-id dataset`.

#### How to normalize unicode (normalize_unicode)
Linguistic data come with a lot of special characters especially for the forms, but also for language names etc. Many of the input methods used for such datasets result in seemingly identical glyphs, which are not necessarily the same unicode character (and are therefore not considered identical by a computer) . Lexedata can normalize unicode across your dataset with the command 
```
python -m lexedata.edit.normalize_unicode
```
You can find more info about what unicode normalization [here](https://towardsdatascience.com/what-on-earth-is-unicode-normalization-56c005c55ad0).

#### Workflow and tracking aid (add_status_column)
When developing and editing a comparative dataset for historical linguistics, you may need to keep track of operations, such as manual checks, input by collaborators etc. You may also wish to inspect manually some of the automatic operations of lexedata. To facilitate such tasks, you can add a "status column" in any of the CLDF tables using the command 
```
python -m lexedata.edit.add_status_column
```
How you use status columns is largely up to you. You may manually keep track of your workflow in this column using specific codewords of your choice. Lexedata scripts that perform automatic operations that are not trivial (such as alignments, automatic cognate set detection) usually leave a message in the status column (which is customizable).  

#### Valid and transparent IDs (simplify_ids)
In a CLDF dataset, all IDs need to be unique and be either numeric or restricted alphanumeric (i.e. containing only leters, numbers and underscores). Lexedata command 
```
python -m lexedata.edit.simplify_ids
```
 verifies that all IDs in the dataset are valid and changes them appropriately if necessary. You can also choose to make your IDs transparent (option `--transparent`) so that you can easily tell what they correspond to. With transparent IDs, instead of a numeric ID, a form will have an ID consisting of the languageID and the parameterID: e.g. the word "main" in French would have the ID stan1290_hand.

#### How to replace or merge IDs (replace_id and replace_id_column)
Sometimes you may need to replace an object's ID (e.g. language ID, concept ID, etc), e.g. if accidentally you have used the same ID twice. Lexedata can replace the id of an object and propagate this change in all tables where it is used as a foreign key (i.e. to link back to that object). The relevant command is
```
python -m lexedata.edit.replace_id TABLE ORIGINAL_ID REPLACEMENT_ID
```
If you intend to merge two IDs, e.g. if you decide to conflate two concepts because they are not distinct in the languages under study, or two doculects that you want to consider as one. you need to use the optional argument `--merge`. Keep in mind that lexedata cannot automatically merge two or more rows in the table in question, so if for example you merged two Language IDs, then you will have two rows in languages.csv with identical IDs. This will cause a warning if you try to validate your dataset (see [CLDF validate](#cldf-validate)). If you want to completely merge the rows, you need to do this by opening the corresponding csv in a spreadsheet or text editor. 

In case you want to replace an entire ID column of a table, then you need to add the new intended ID column to the table and use the command
```
python -m lexedata.edit.replace_id_column TABLE REPLACEMENT
```


### Operations on FormTable

#### Merge polysemous forms (merge_homophones)
In large datasets, there may be identical forms within the same language, corresponding to homophonous or polysemous words. You can use 
```
python -m lexedata.report.homophones
```
 to detect identical forms present in the dataset (see [detect potential homophonous or polysemous forms](#detect-potential-homophonous-or-polysemous-forms)). Once you decide which forms are in fact polysemous, you can use  
```
python -m lexedata.edit.merge_homophones MERGE_FILE
```
  in order to merge them into one form with multiple meanings. The MERGE_FILE contains the forms to be merged, in the same format as the output report from the `lexedata.report.homophones` command. There are multiple merge functions available for the different metadata associated with forms (e.g. for comments the default merge function is concatenate, while for sources it is union). If you need to modify the default behavior of the command you can use the optional argument `--merge COLUMN:MERGER`, where COLUMN is the name of the column in your dataset and MERGER is the merge function you want to use (from a list of functions that can be found in the help).

#### Segment forms (add_segments)
In order to align forms to find correspondence sets and for automatic cognate detection, you need to segment the forms included in your dataset. Lexedata can do this automatically using [CLTS](http://clts.clld.org). To use this functionality type
```
python -m lexedata.edit.add_segments TRANCRIPTION_COLUMN
```
where transcription column refers to the column that contains the forms to be segmented (the #form column by default). A column "Segments" will be added to your FormTable. The segmenter makes some educated guesses and automatic corrections regarding segments (e.g. obviously wrong placed tiebars for affricates, non-IPA stress symbols, etc). All these corrections are listed in the segmenter's report for you to review. You may choose to apply these corrections to the form column as well, using the switch `--replace_form`.


### Operations on ParameterTable (concepts)

#### Linking concepts to Concepticon (add_concepticon)
Lexedata can automatically link the concepts present in a dataset with concept sets in the [Concepticon](https://concepticon.clld.org/). The relevant command is
```
python -m lexedata.edit.add_concepticon
```
Your ParameterTable will now have a new column: Concepticon ID, with the corresponding ID of a concept set in Concepticon. We recommend that you manually inspect these links for errors. In order to facilitate this task, you can also add columns for the concept set name (`--add_concept_set_name`) and the concepticon definition (`--add_definitions`). Finally, if your ParameterTable contains a Status Column (see [workflow and tracking aid](#workflow-and-tracking-aid-add_status_column)), any links to the Concepticon will be tagged as automatic, or you can define a custom message using `--status_update "STATUS UPDATE"`.

### Operations on CognateTable (judgements) and CognatesetTable

#### Adding central concepts to cognate sets (add_central_concepts)

If you are using cross-concept cognate sets, and you want to assign each cognate set to a certain concept (e.g. for the purposes of assigning absences in root presence coding), you can use lexedata to automatically add central concepts to your cognate sets. The central concept of each cognateset will be used as a proxy for assigning absences: If the central concept is attested in a language with a different root, then the root in question will be coded as absent for this language (see the glossary for more explanations for central concepts, coding methods and absence heuristics for root presence coding). 

The central concept of each cognate set is determined by the [CLICS](http://clics.clld.org) graph of all the concepts associated with this cognate set (this requires having your concepts linked to the Concepticon). The concept with the highest centrality in the CLICS graph will be retained as the central concept. In the absence of Concepticon links, the central concept is the most common concept. In order to add central concepts to your dataset, type

```
python -m lexedata.edit.add_central_concepts
```
.
This will add a #parameterReference column to your CognatesetTable containing the central concept. You can of course manually review and edit the central concepts. If you rely on central concepts for coding and you heavily edit your cognate judgements, consider re-assigning central concepts with the switch `--overwrite`.


#### Adding trivial cognate sets (add_singleton_cognatesets)

Depending on your workflow, you may not have assigned forms to trivial (singleton) cognate sets, where they would be the only members. This could also be true for loanwords that are products of separate borrowing events, even if they have the same source. You can automatically assign any form that is not already in a cognate set to a trivial cognate set of one member (a singleton cognate set) using the command 
```
python -m lexedata.edit.add_singleton_cognate_sets
```
If you want to be careful about morphology, you can tell this script to create singletons for every uncoded set of segments by using
```
python -m lexedata.edit.add_singleton_cognate_sets --by-segment
```
This will create a separate cognate set for every contiguous slice of segments that are not in any cognate set yet, eg. one for the prefix and a separate one for the suffix of a word with a stem that is already coded.

#### Merging cognate sets

You can write a file listing cognate sets to be merged into one and feed it to 
```
python -m lexedata.edit.merge_cognate_sets MERGEFILE
```
which bulk-merges these cognatesets. The main use of this command is to merge cognatesets found to be strongly overlapping by the [nonconcatenative morphemes](#nonconcatenative-morphology) report.

## Reporting and checking data integrity (lexedata.report)

The report package contains scripts that check for data integrity and generate reports for your dataset. You can use these reports to identify potential problems in the dataset, to track your progress, or to report statistics in publications (e.g. coverage for each language in a dataset).

### Language coverage
You can obtain various statistics related to coverage (how many concepts have corresponding forms in each language) with the command 
```
python -m lexedata.report.coverage
```

Among others, you can find which languages have corresponding forms for specific concepts, which languages have at least a given coverage percentage etc. NA forms (that correspond to concepts that do not exist in a particular language) by default count towards coverage, while missing forms don't. You can customize the treatment of missing and NA forms with the optional argument `--missing`.

### Segment inventories
You can get a report on all segments used for each language and their frequency in the dataset by typing 
```
python -m lexedata.report.segment_inventories
```
This can be useful to locate rare or even erroneous transcriptions, non-standard IPA symbols etc.
You can subset the report to one or a smaller number of languages for clarity using `--languages`.

### Detect potential homophonous or polysemous forms
In large datasets, you may have identical forms associated with different concepts. This could be the case because there are homophonous, unrelated forms, or because there is in fact one underlying polysemous form. Lexedata can help you detect potential homophones or polysemies by using the command

```
python -m lexedata.report.homophones
```
The output of this command is a list of all groups of identical forms in the data and their associated concepts, along with the information if the associated concepts are connected in CLICS or not (if your concepts are linked to Concepticon, see [linking concepts to Concepticon](#linking-concepts-to-concepticon-add_concepticon)). You can choose to merge the polysemous forms, so you have one form associated to multiple concepts. In order to perform this operation, edit the output file of `lexedata.report.homophones`, so that only the groups of forms that are to be merged remain and then use `lexedata.edit.merge_homophones` (see [merge polysemous forms](#merge-polysemous-forms-merge_homophones)).

### Non-concatenative morphology
You can get a detailed report on potentially non-concatenative morphemes (segments that belong to more than one cognate sets, or cognate sets that refer to segments in a form which don't simply follow each other, due to infixes/circumfixes or metathesis) by running 
```
python -m lexedata.report.nonconcatenative_morphemes
```
For a report on cognate judgements more focused on structural integrity, see [cognate judgements](#cognate-judgements).

The `nonconcatenative_morphemes` command outputs a report of clusters of cognate sets that have an overlap of 50% in at least one form. As such, it indicates that these cognate sets may be candidates that could be merged. Like the [segment inventories](#segment-inventories) report, you can output this report to a file and edit it before feeding it into the [cognateset merger command](merging-cognate-sets). This command has a very similar interface to the homophones merger, and in fact a main use case is

1. [Detecting homophones](#detect-potential-homophonous-or-polysemous-forms)
2. [Merging homophones into polysemous forms](#merge-polysemous-forms-merge-homophones))
3. Detecting the pairs of cognate sets that now both point to the same newly-merged polysemous form, using this script
4. [Merging those cognatesets](#merging-cognate-sets)


### Cognate judgements
The cognate judgement report checks for issues involving cognate judgements, the segment slice column, the referenced segments and the alignment. For example, it checks if the referenced segments match what is present in the alignment and are contiguous (including identically looking but underlyingly different unicode characters), if the segment slice is valid based on the length of the form, and if the length of all alignments in a cognateset match. It also checks that missing ("") and NA ("-") forms are not assigned to any cognate set. In order to obtain the judgements report, you can use the command 
```
python -m lexedata.report.judgements
```
This report is part of the checks that the extended [CLDF validate](#cldf-validate) executes, because it focuses on potential issues in the data model (eg. ‘alignments’ of different length, which makes them invalid as alignments).
If you want additionally to check for cognatesets that contain non-contiguous segments (eg. because they skip an infix), you can use the switch `--strict`; this switch is not available through `extended_cldf_validate`. A more extensive report about the structure of segments inside cognate sets can be obtained for the [non-concatenative morphology report](#nonconcatenative-morphology).

### CLDF validate
Before and after a variety of operations with lexedata, and especially after manual editing of raw data, it is highly recommended to validate your dataset so you can catch and fix any inconsistencies. You can do a basic validation using the relevant command in the `pycldf` package, or an extended one with lexedata. For the basic validation, type: `cldf validate METADATA`, where `METADATA` stands for the metadata (json) file of your dataset.
For the extended cldf validation, type 
```
python -m lexedata.report.extended_cldf_validate
```
The extended validation includes all operations of the basic pycldf command, but also checks further potential issues related to cognate judgements, unicode normalization, internal references, etc.

### Filter dataset
The `filter` command gives you the possibility to filter any table of your dataset according to a particular column using regular expressions. You can use this command to output a subset of the dataset to a file and use it as input for further commands in lexedata (in particular for the subsetting operations supported by various commands) or other downstream analyses. The command is 
```
python -m lexedata.report.filter COLUMN FILTER [TABLE]
```
, where `COLUMN` is the column to be filtered, the `FILTER` the expression to filter by and `TABLE` the table of the dataset that you want to filter. For more details, refer to the command's help.


## Exporting data (lexedata.exporter)

The `exporter` package contains two types of scripts.

1. Scripts which export the data to make it available for editing, through an [xlsx cognate matrix](#the-xlsx-cognate-matrix-loop) or through [Edictor and LingPy](#the-edictor-editing-loop). These export scripts come with a corresponding importer script in `lexedata.importer`, so that data can be exported, edited externally, and re-imported.
2. Scripts which export the data for other use. The [matrix exporter](#export-as-wordlist-matrix) generates a comparative word list that can be edited for inclusion in a publication, while the [phylogenetics exporter](#export-coded-data-for-phylogenetic-analyses) generates character sequences that can be used in phylogenetics software.

### The xlsx cognate matrix loop

Lexedata offers the possibility to edit and annotate within- or across-concept cognate sets in a spreadsheet format using the spreadsheet
editor of your choice (we have successfully used Google sheets, LibreOffice Calc and Microsoft
Excel, but it should work in principle on any spreadsheet editor). In order to
use this functionality, you export your cognate judgements to a
cognate matrix (in xlsx format) which you can edit, and then re-import this modified cognate matrix
back into your cldf dataset. This process will overwrite previously
existing cognate sets and cognate judgements, as well as any associated comments
(CognateTable comments and CognatesetTable comments).

```{important}
You cannot edit the raw data (forms, translation, form comments, etc.)
through this process. To edit raw data, see [editing a CLDF dataset](#editing-a-cldf-dataset-lexedataedit).
```

It is always a good idea to validate your dataset before and after any edits to make sure that everything is linked as it should in the cldf format.
You can use `cldf validate METADATA_FILE` or 
```
python -m lexedata.report.extended_cldf_validate
```
 for a more thorough check (see also [CLDF validate](#cldf-validate)). The latter is particularly useful, because it checks a lot of additional assumptions about cognate judgements.

In order to export an xlsx cognate matrix, you should type
```
python -m lexedata.exporter.cognates FILENAME.xlsx
```
The cognate matrix will be written to an excel file with the specified name.
There are optional arguments to sort the languages and the cognate sets in this table, as well as to assign any forms not currently in a cognate set to automatic singleton cognate sets (see command help for more information; see also: [lexedata.edit.add_singleton_cognatesets](#adding-trivial-cognate-sets-add-singleton-cognatesets)). 

You can open and edit the cognate matrix in the spreadsheet editor of your
choice. You can update cognate sets, cognate judgements and associated metadata
(in particular segment slices, alignments, CognateTable comments, and CognatesetTable comments). This workflow can allow
specialists to work on the cognacy judgements in a familiar format (such as
excel), or allow a team to work collaboratively on Google sheets, while at the
same time keeping the dataset in the standard cldf format. You just need to
remember that you need to preserve the general format in order to reimport your
modified cognate sets into your cldf dataset.

#### Re-importing cognate sets from a cognate matrix

You can reimport the cognate matrix xlsx spreadsheet by typing:

```
python -m lexedata.importer.cognates FILENAME.xlsx
```

This will re-generate the CognateTable with the cognate judgements, as well as
the CognatesetTable, in your CLDF dataset according to the cognate matrix.

### The Edictor editing loop

The ‘etymological dictionary editor’ [EDICTOR](https://edictor.digling.org)
provides access to another way of modifying cognate sets and alignments, with
interfaces for partial cognate annotation, a graphical alignment editor and
summaries of sound correspondences. Like the [LingPy](http://lingpy.org/) Python
library for historical linguistics, Edictor uses a format that is similar to
CLDF's form table, but it also includes cognate judgements and alignments. In addition, it differs in several format choices that look minor to the
human eye, but matter greatly for automatic processing by a computer.

To work with CLDF data in Edictor or LingPy, Lexedata provides a pair of an exporter and importer script

```
python -m lexedata.exporter.edictor FILENAME.tsv
python -m lexedata.importer.edictor FILENAME.tsv
```

which allow the exporting of a CLDF dataset to Edictor's TSV format and importing the data back after editing.

```{Important}
This loop is brittle.

* Edictor can sometimes halt processing without warning, in particular on large datasets or datasets with special assumptions, such as non-concatenative morphemes, polysemous forms, or multi-line comments.
* Such datasets also quickly become unwieldy in Edictor.
* In order to support edits using Edictor better, the exporter allows the restriction of the dataset to a subset of languages and concepts. The importer does its best to try integrating the changes made in Edictor back to the dataset. However, there are a lot of special cases which are insufficiently tested.

Be careful with the Edictor loop. Re-import often, commit often to be able to undo changes, and don't hesitate to [raise an issue](https://github.com/Anaphory/lexedata/issues/new) concerning undesired behavior.
```

### Export a comparative wordlist

In particular for the supplementary material of a publication, it is often
useful to provide a comparative word list in a human-readable layout in addition
to a deposited archive of the CLDF dataset (eg. on [Zenodo](https://zenodo.org)
or [figshare](https://figshare.com/)). The command

```
python -m lexedata.exporter.matrix FILENAME.xlsx
```

helps preparing such a layout. It generates an Excel sheet which contains one column per language and one row per concept. Optionally, forms can be hyperlinked to their corresponding page or anchor in a web-browsable database version of the dataset, while concepts can be output with their Concepticon links. Also, you can specify a subset of languages and concepts to include, eg. only the {term}`primary concept`s.

### Export coded data for phylogenetic analyses

Lexedata is a powerful tool to prepare linguistic data for phylogenetic
analyses. The command `python -m lexedata.exporter.phylogenetics` can be used to export a cldf dataset containing cognate judgements
as a coded matrix for phylogenetic analyses to be used by standard phylogenetic
software, (such as [BEAST2](http://www.beast2.org/), [MrBayes](http://nbisweden.github.io/MrBayes/) or [revBayes](https://revbayes.github.io/)). Different formats are supported,
such as nexus, csv, a beast-friendly xml format, as well as a raw alignment
format (similar to the FASTA format used in bioinformatics). Lexedata also
supports different coding methods for phylogenetic analyses: {term}`root-meaning coding`,
cross-concept cognate sets AKA {term}`root presence coding`, and {term}`multistate coding`.

Finally, you can use Lexedata
to filter and export a portion of your dataset for phylogenetic analyses, e.g.
if some languages or concepts are not fully coded yet, or if you want to exclude
specific cognate sets that are not reviewed yet.

