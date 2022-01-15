A short introduction to the command line
========================================

While you may be used to driving applications by pointing and clicking
with the mouse and very occasionally typing text, command-line
interfaces (CLI) use text commands to drive computer programs.
In some sense similar to human language, these text commands must obey
a specific syntax to be understood. However, unlike human language,
if you don't follow the syntax exactly, nothing will happen. This syntax powers compositionality, which makes automating complex
or repetitive tasks easier – so it is appropriate for lexedata.

All lexedata tools are run from the command line, according to principles
explained in the :doc:`Manual`. There are other excellent introductions to the
power of the command line, but if you are completely new to it, the following
section may help you get started.

Navigation using the command line
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can navigate to a specific folder using the command line on your terminal
(also ‘console’ or ‘command prompt’ or ‘CMD’) as follows: You can see the
directory (folder) you are in at the moment (current directory) within the
prompt. In order to go to a directory below (contained in the current
directory), type ``cd [relative directory path]`` (``cd`` stands for *change
directory*), e.g. ``cd Documents/arawak/data``.

If you do not know the path you want to get to, you can open it in your file
browser (eg. Finder or Explorer) and usually find it there, either in an address
bar or in the folder properties. Sometimes, it also works to drag-and-drop the
folder into your terminal.

Note that directory names are case sensitive and that they can be automatically
filled in (if they are unique) by pressing the tab key. In order to go to a
directory above (the directory containing the current directory), type ``cd ..``.
Note that you can type any path combining up and down steps. So, if I am in the
data directory given as an example above, in order to go to the directory
maweti-guarani which is within Documents, I can type ``cd ../../maweti-guarani``.

At any point you can see the contents of your current directory by typing ``ls``
or ``dir``, depending on your operating system. (Don't worry about typing the
wrong one: the worst to happen is your system telling you “I don't know that
command.”)
