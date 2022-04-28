---
title: 'Lexedata: A toolbox to edit CLDF lexical datasets'
tags:
  - Python
  - linguistics
  - wordlist
  - cross-linguistic data format
authors:
  - name: Gereon A. Kaiping
    orcid: 0000-0002-8155-9089
    affiliation: 1
  - name: Melvin S. Steiger
    orcid: 0000-0001-7300-0704
    affiliation: 2
  - name: Natalia Chousou-Polydouri
    orcid: 0000-0002-5693-975X
    affiliation: "2,3"
affiliations:
 - name: Department of Geography, Universität Zürich, CH
   index: 1
 - name: Department of Comparative Linguistics, Universität Zürich, CH
   index: 2
 - name: Center for the Interdisciplinary Study of Language Evolution, Universität Zürich, CH
   index: 3
date: 20 April 2022
bibliography: bibliography.bib
doi: https://doi.org/10.21105/joss.04140
citation: Kaiping et al., (2022). Lexedata: A toolbox to edit CLDF lexical datasets. Journal of Open Source Software, 7(72), 4140, https://doi.org/10.21105/joss.04140
---
# Summary
Lexedata is a collection of tools to support the editing process of comparative
lexical data. Wordlists are a comparatively easily
collected type of language documentation that is nonetheless quite data-rich and useful for the systematic
comparison of languages [@list2021lexibank]. They are an important resource in
comparative and historical linguistics, including their use as raw data for
language phylogenetics [@gray2009language;@grollemund2015bantu].

The `lexedata` package uses the “Cross-Linguistic Data Format” (CLDF,
@cldf11, @cldf-paper) as the main data format for a relational database containing
forms, languages, concepts, and etymological relationships. The CLDF
specification builds on top of the CSV for the Web (CSVW,
@pollock2015metadata) specs by the W3C, and as such consists of one or more
comma-separated value (CSV) files that get their semantics from a metadata file
in JSON format.

Implemented in Python as a set of command line tools, Lexedata provides various
helper functions to address issues that frequently arise when working with comparative wordlists
for multiple languages, as shown in \autoref{fig:structure}. These include
importing from and exporting to formats more familiar to linguists, as well as bulk edit functions
and associated integrity checks. For example, there
are scripts for importing data from MS Excel sheets of various common formats
into CLDF, checking for homophones, manipulating etymological
judgements, and exporting coded datasets for use in phylogenetic software.

![Overview of the functionality in Lexedata.\label{fig:structure}](structure.pdf)

# Statement of Need

Maintaining the integrity of CLDF as a relational database is difficult using
general CSV editing tools. This holds in particular for the usual dataset size
of hundreds of languages and concepts, and formats unfamiliar to most linguists.
Dedicated relational database software, which simplifies the maintenance of the
data constraints, would set an even bigger hurdle to researchers, even to those
who are reasonably computer-savvy.

The major existing tool for curating lexical datasets in other formats and
providing them as CLDF for interoperability is cldfbench [@cldfbench]. However,
cldfbench assumes that the data curator is not necessarily in a position to
edit the dataset. As such, it provides a very flexible interface to
transform and curate CLDF datasets, at the cost of making this accessible
through an API which requires writing Python code.

Given that the majority of comparative linguists are unfamiliar with programming,
Lexedata is designed to not need any programming skills. In contrast with
cldfbench, Lexedata is written for the purpose of not only curating, but also
collecting and editing the dataset. It therefore imposes additional constraints
on the dataset which are very useful in editing tasks, but not strictly required
by CLDF.

There are two major existing tools for editing lexical datasets, LingPy
[@lingpy] and Edictor [@edictor]. Edictor is a browser-based graphical user
interface tool to edit cognate annotations, while LingPy is a Python library
focused on automating manipulations of lexical datasets, such as automatic
cognate detection. Both of these pre-date the CLDF format, and while their
common data format inspired some features of CLDF, it has some differences.
Lexedata provides export and import functionality for this TSV-based format to
and from CLDF. In addition, Lexedata exposes a major LingPy functionality, the
Automatic Cognate Detection (ACD, @list2017potential) using Lexstat
[@list2012lexstat], to work directly on CLDF datasets. This avoids both memory
issues arising from LingPy's approach to load the entire dataset into memory and
the need to convert between CLDF and LingPy.

Lexedata is designed to facilitate adding comments to cognate sets and cognate
judgements, through the annotation tools in the Excel format (which naturally
extend to comment threads in Google Sheets for collaborative editing), as well as
tracking the editing workflow through status columns with customizable messages.
Last but not least, to ensure that the user retains a good sense of control and overview,
Lexedata includes helpful warning messages that suggest potential solutions and next
steps to the user, while it keeps the user informed about batch operations with
intermediate info messages and final reports.

In summary, Lexedata addresses the need to curate and edit a lexical dataset in
CLDF format without the ability to program, which is still a rare skill among
comparative linguists. It allows this without sacrificing the power and
familiarity of existing software, such as GUI spreadsheed apps or Edictor, and by
providing user-friendly access to format conversions and bulk editing functionality 
through simple terminal commands.

# Research use
The extensive lexical dataset editing functionality is currently used by projects
at UC Berkeley and Universität Zürich for Arawakan and Mawetí-Guaraní languages
and at Universiteit Gent for Bantu.
Precursor scripts have also been used for Timor-Alor-Pantar and Austronesian languages [@lexirumah-paper].
The export to phylogenetic alignments, derived from BEASTling
[@maurits2017beastling;@beastling14], has been used in different language
phylogenetics projects that are already under review
[@kaiping2019subgrouping;@gunnink2022bantu].

# Acknowledgement
Development of Lexedata was funded by the Swiss National Science Foundation
(SNSF) Sinergia Project “Out of Asia” CRSII5_183578.

# References
