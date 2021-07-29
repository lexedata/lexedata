---
title: 'Lexedata: A Python toolbox to edit CLDF lexical data sets'
tags:
  - Python
  - linguistics
  - wordlist
  - cross-linguistic data format
authors:
  - name: Gereon A. Kaiping
    orcid: 0000-0002-8155-9089
    affiliation: 1
  - name: Natalia Chousou-Polydouri
    orcid: 0000-0002-5693-975X
    affiliation: 2
affiliations:
 - name: Department of Geography, Universität Zürich, CH
   index: 1
 - name: Department of Comparative Linguistics, Universität Zürich, CH
   index: 2
date: 21 July 2021
bibliography: paper.bib
---
# Summary
Lexedata is a collection of tools to support the editing process of comparative
lexical data. As a type of language documentation that is comparatively easily
collected [@...] and nonetheless quite rich in data useful for the systematic
comparison of languages [@...], word-lists are an important resource in
comparative and historical linguistics, including their use as raw data for
language phylogenetics [@...].

The `lexedata` package uses the “Cross-Linguistic Data Format” (CLDF, [@cldf])
as main data format. This specification builds on top of the CSV for the Web
(CSVW, [@csvw]) specs by the W3C, and as such consists of one or more
comma-separated value (CSV) files that get their semantics from a metadata file
in JSON format.

The individual Python scripts, with shared assumptions and interfaces, implement
various helper functions that frequently arise when working with comparative
word-lists for multiple languages, such as importing data from MS Excel sheets
of various common formats into CLDF, splitting  Automatic Cognate Detection (ACD, [@acd])
using Lexstat [@lexstat] 


# Statement of Need
section that clearly illustrates the research purpose of the software.
# Research use
Mention (if applicable) a representative set of past or ongoing research projects using the software and recent scholarly publications enabled by it.
# Acknowledgement
of any financial support.
# A list of key references
including to other software addressing related needs. Note that the references should include full names of venues, e.g., journals and conferences, not abbreviations only understood in the context of a specific discipline.
