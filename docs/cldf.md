# The CLDF format
The CLDF format is designed for sharing and reusing comparative linguistic data. A CLDF lexical dataset consists of a series of .csv files, a metadata .json file describing the structure of each .csv file and their inter-relationships, and a .bib file containing the relevant sources. A typical CLDF lexical dataset consists of the following .csv files: languages.csv, parameters.csv (listing concepts), forms.csv, cognatesets.csv, and cognates.csv. Not all files are necessary: the bare minimum for a valid CLDF dataset is forms.csv. However, lexedata requires a metadata json file for almost every operation.

Each .csv file has to have an ID column. Below, we briefly describe the typical files of a lexical CLDF dataset and how they interact with Lexedata when necessary. For each file, you can find below the necessary columns and typical columns. You can always add any custom columns as needed for your dataset. There is also the possibility to add further .csv files depending on your needs. For more information on the CLDF format, you can refer to https://cldf.clld.org/.

We recommend that you keep all these files in one folder which is versioned with git. You can use Github or Gitlab for this purpose, see section 1.3 below.

## languages.csv
The file `languages.csv` contains the different varieties included in your lexical dataset and their metadata. Every row is a variety.

 - Necessary columns: Language_ID
 - Typical columns: Name


## parameters.csv
The `parameters.csv` (sometimes also named `concepts.csv` in datasets with manually created metadata) contains the different concepts (meanings) included in your lexical dataset. Every row is a concept.

 - Necessary columns: Concept_ID
 - Typical columns: Name, Definition, Concepticon_ID

## forms.csv
The FormTable, contained in a file usually named `forms.csv`, is the core of a lexical dataset.
A well-structured `forms.csv` on its own, even without accompanying metadata, can already be understood as a lexical dataset by many CLDF-aware applications.
The table contains all the different forms included in your dataset. Every row is a form. To add page numbers for the sources in the cldf format, you should use the format source[page]. You can have different page numbers and page ranges within the square brackets (e.g. `smith2003[45, 48, 52-56]`).

 - Necessary columns: Form_ID, Form, Concept_ID, Language_ID
 - Typical columns: Comment, Segments, Source

## cognatesets.csv
Cognatesets.csv contains the cognate sets included in your dataset and their metadata. Every row is a cognate set. Note that, depending on the dataset, cognate set here can either mean cross-concept cognate set (all forms descending from the same protoform), or root-meaning set (all forms descending from the same protoform that have the same meaning). Lexedata is capable of automatically deriving root-meaning sets from cross-concept cognate sets, but the reverse is of course not possible.
Necessary columns: Cognateset_ID
Typical columns: Comment, Source

## cognates.csv
Cognates.csv contains all the individual cognate judgements included in the dataset, i.e. it links every form to the cognateset it belongs to. Note that it is possible to have forms belonging to multiple cognate sets (e.g. to account for partial cognacy). 
<!--TO DO: add reference to somewhere, where more complex datasets are explained. 
 NCP: what was the intent of this comment? Should we have a section on partial cognacy?-->
Necessary columns: Cognate_ID, Form_ID, Cognateset_ID
Typical columns: Comment

## sources.bib
This is a BibTeX file containing references to all sources used in the dataset. The entries in the Source column of the forms.csv (or any other table) must be identical to a handle (unique code) of a reference in the `sources.bib`.

## Wordlist-metadata.json
The Wordlist-metadata.json file contains a detailed description of all the CSV files, their columns and their interrelationships. It is not required file for a CLDF dataset, but it is necessary for the vast majority of operations using lexedata. For simple datasets, lexedata can create automatically a json file (see section XXX). However, for more complex datasets, you would need to provide one yourself.
<!--- TODO: add some support for making a json file--->

For an example of a simple .json file, see XXX. Every change to the structure of the dataset (e.g. insertion or deletion of a column in any file) needs to be reflected in the .json file for the dataset to be a valid cldf dataset.
<!-- TO DO: add a reference to sample files and sample datasets --> 
Below you can see a typical description of a .csv file in the .json file.

![](figures/json.png)

