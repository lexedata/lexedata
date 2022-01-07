Lexedata installation instructions
==================================

1. In order to install and use Lexedata you need to have Python 3.7 (or newer) installed.

If you are unsure if this is the case, open a terminal window and type ``python
--version``. If Python 3.7 (or newer) is installed you will see the version. If you don't have
any version of Python or it is a version of Python 2, then you need to download
and install Python 3. There are different distributions of Python and most of
them should work. A popular one that we have tested is
`Anaconda <https://www.anaconda.com/products/individual>`_. Once you have
downloaded and installed Anaconda close and open the terminal again and type
``python --version`` again. You should see the current version of Python 3 you
just downloaded.

If you are ever stuck with the python prompt, which starts with ``>>>``, in
order to exit Python type ``quit()``.

3. Install the lexedata package.
In your terminal window type ``pip install lexedata``. 

This will install lexedata and all its dependencies on your computer and make it
automatically updatable every time you pull a new version of the Lexedata
repository from GitHub. Now you should be ready to use lexedata!

# Updating lexedata and Catalogs

You can update lexedata when their is a new release by typing ``???``.
Lexedata is dependent on various other packages, and is using catalogs, such as Glottolog, CLTS, and Concepticon. It is good to update those once in a while to get the most up-to-date information. You can update all three catalogs by typing ``cldfbench catupdate``.
