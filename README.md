# lexedata

![lexedata: edit lexi data](lexedata.png)

Lexedata is an open source Python package that includes a collection of command line tools to edit comparative lexical data in the CLDF format (https://doi.org/10.1038/sdata.2018.205), which adds an ontology of terms from comparative linguistics (https://cldf.clld.org/v1.0/terms.html) to the W3C “CSV for the Web” (csvw, https://w3c.github.io/csvw/) standard. The package includes tools to run batch-editing operations as well as tools to convert CLDF to and from other data formats in use in computational historical linguistics.

The documentation for Lexedata can be found on [ReadTheDocs.IO](https://lexedata.readthedocs.io/en/latest/).

The package is available from [PyPI](https://pypi.org/project/lexedata/). If you have a recent Python installation, you can easily install it using

    pip install lexedata
    
More detailed installation instructions can be found [in the documentation](https://lexedata.readthedocs.io/en/stable/installation.html).

Lexedata was developed from the practical experience of editing several specific different lexical data sets, but generalizes beyond the specific datasets. The aim is to be helpful for editors of other lexical datasets, and as such we consider lacking documentation and unexpected, unexplained behaviour a bug; feel free to [raise an issue on Github](https://github.com/Anaphory/lexedata/issues/new/choose) if you encounter any.
