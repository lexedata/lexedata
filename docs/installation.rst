Installation
============

1. In order to install and use Lexedata you need to have Python 3.8 (or newer) installed.

If you are unsure if this is the case, open a terminal window and type ``python
--version``. If Python 3.7 (or newer) is installed you will see the version. If you don't have
any version of Python or it is a version of Python 2, then you need to download
and install Python 3. There are different distributions of Python and most of
them should work. A popular one that we have tested is
`Anaconda <https://www.anaconda.com/products/individual>`_. Once you have
downloaded and installed Anaconda, close and open the terminal again, and type
``python --version``. You should see the current version of Python 3 you
just downloaded.

If you are ever stuck with the python prompt, which starts with ``>>>``, type ``quit()`` in
order to exit Python.

2. Install the lexedata package.

In your terminal window type ``pip install lexedata``. 
This will install lexedata and all its dependencies on your computer. Now you should be ready to use lexedata!

3. Install CLDF catalogs

Lexedata uses CLDF catalogs, `Glottolog <http://glottolog.org>`_ for languages,
`CLTS <http://clts.clld.org>`_ for phonetic transcription symbols, and
`Concepticon <http://concepticon.clld.org>`_ for concepts, in some of its
scripts. You can install them using ``cldfbench catconfig``, it will prompt you
about the installation process and download and install those catalogs. Make
sure to *agree* to cloning the three repositories (`[y/N]`_ defaults to “No” for
each catalog) and you will end up with local copies of them.

Updating lexedata and Catalogs
------------------------------

You can update lexedata when there is a new release by typing ``pip install --upgrade lexedata``. This will also update all the packages that lexedata is dependent on. However, the CLDF catalogs, (Glottolog, CLTS, and Concepticon) are not automatically updated. It is good to update those once in a while to get the most up-to-date information, by typing ``cldfbench catupdate``.
