Working with git
================

Git is a version control system. It keeps track of changes so you can easily
revert to an earlier version or store a snapshot of your project (e.g. the state
of the dataset for a particular article you published). While you could use
Lexedata without git, we highly recommend storing your data in a repository
(folder) versioned with git. In this section we are going to cover some basic
commands to get you started. You can find more detailed instructions and more
information in `begin with git
<https://product.hubspot.com/blog/git-and-github-tutorial-for-beginners>`_ and
also in the `tutorials by Github <https://guides.github.com/>`_. You can also
download and use the GitHub Desktop application if you prefer to not use the
:doc:`command line <cli>` to interact with GitHub. However, you do need to use
the command line to interact with lexedata.

Setting up git
~~~~~~~~~~~~~~

If you start with your own blank slate for a dataset, a ``git init`` in your
dataset folder will set it up as a git repository. If you have a template or a
dataset already on Github, ``git clone https://github.com/USERNAME/REPOSITORY``
will create a local copy for you. (You can manually move that local copy on your
computer in case it ended up in the wrong place.)

Git may expect some more setup, e.g. to know your name and an email address to be
credited as author of changes you commit, but it is generally good at telling
you these things.

Basic git commands
~~~~~~~~~~~~~~~~~~

Below we are going to describe the use of the most basic git commands. We assume a setup with a local git repository (on your computer) and a remote repository (e.g. on GitHub).

``git fetch``: This command "informs" the git on your computer about the status of the remote repository. It does *not* update or change any files in your local repository.

``git status``: This commands gives you a detailed report of the status of your local repository, also in relation to your remote repository. In the report you can see any changes that you have done to your local repository, and if they are commited or not, as well as any committed changes that have happened in the remote repository in the meantime.

``git pull``: With this command you can update your local repository to be identical to the remote one. This will not work if you have uncommitted changes in your local repository to protect your work.

``git add FILENAME``: This command adds new or modified files to git, or it "stages" the changes to be committed.

``git commit -m "COMMIT MESSAGE"``: After adding (or staging) all the changes that you want to commit, you can use this command to commit the changes to your local repository with an associated commit message. Typically the commit message contains a summary of the changes. This command will *not* update the remote repository.

``git push``: This command will push (or publish) your local commits to the remote repository, which will be updated to reflect these new changes.

To ensure dataset integrity, we recommend running ``cldf validate Wordlist-metadata.json`` before committing and pushing, so that any cldf errors are caught and corrected (see :ref:`cldf-format-validation`)).

