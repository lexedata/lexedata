# `lexedata` Manual

## Lexedata installation instructions

The following instructions are for MacOS computers. Instructions for other operating systems will follow.

#### 1. In order to install and use Lexedata you need to have Python 3 installed.
If you are unsure if this is the case, open a terminal window and type `python`. 
If Python 3 is installed you will see the version, the date of the installation etc. If you don't have any version of Python or it is a version of Python 2, then you need to download and install Python 3. 
There are different distributions of Python and most of them should work. A popular one that we have tested is Anaconda and can be downloaded [here](https://www.anaconda.com/products/individual).
Once you have downloaded and installed Anaconda close and open the terminal again and type `python`. You should see the current version of Python 3 you just downloaded.
In order to exit Python type `quit()`.

#### 2. The next step is to clone the Lexedata repository from GitHub on your computer.
You can do this through the command line or through the GitHub desktop application (follow the instructions/tutorial within the GitHub desktop applications).
If using the command line, in the terminal window, navigate to the folder where you would like to put the Lexedata folder. Then type `git clone https://github.com/Anaphory/lexedata`.
This should create a folder called lexedata in the selected location.

#### 3. Install the lexedata package.
In your terminal window type `pip install --user -e ./lexedata`. This will install lexedata and all its dependencies on your computer and make it automatically updatable every time you pull a new version of the Lexedata repository from GitHub.
Now you should be ready to use lexedata!

## Importing a lexical dataset to lexedata

## Adding a new language/new data to an existing lexical dataset in lexedata

## How to edit data in lexedata

There are two ways to edit data in lexedata: through the web interface (under construction) and through editing the .csv files in your corresponding GitHub repository.

## Cognate Table export-import loop

Lexedata offers the possibility to edit and annotate cognate set (or root-meaning set) judgements in a spreadsheet format using the spreadsheet editor of your choice (we have successfully used Google sheets and Microsoft Excel, but it should work in principle on any spreadsheet editor).
In order to use this functionality, fist you need to export your cognate judgements in a Cognate Table (in xlsx format) and then re-import the modified Cognate Table back into your lexedata lexical dataset. 
This process will overwrite previously existing cognate sets and cognate judgements, as well as any associated comments (cognate comments and cognate judgement comments).
IMPORTANT: you cannot edit the raw data (forms, translation, form comments etc) through this process. Instead see XXX how to edit form data in lexedata.

#### 1. Validate your dataset using the cldf validate command
It is always a good idea to validate your dataset before and after any edits to make sure that everything is linked as it should in the cldf format.
To perform this test, navigate to your lexical dataset repository and type `cldf validate Wordlist-metadata.json`. Assuming that there are not any errors or warnings you need to take care of, you can proceed to the next step.

#### 2. Export the Cognate Table
Type `python -m lexedata.exporter.cognates`. The .xlsx file (Cognate Table) will be created in your dataset repository. 

#### 3. Open and edit the Cognate Table in a spreadsheet editor

#### 4. Re-import the Cognate Table in lexedata
Once you have edited and/or annotated the Cognate Table, you can update your dataset by re-importing it. Type `python -m lexedata.importer.cognates`. 

#### 5. Run cldf validate once more on your dataset (see step 1)

#### 6. Commit and Push (publish) your new version on your dataset repository
