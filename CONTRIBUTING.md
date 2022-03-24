# Contributing

Thank you for your interest in Lexedata's development! You don't need to be a software developer yourself to make a contribution to the package.

## Found a Bug, or a point of confusion in the documentation?

If you find a bug in the source code, you can help us by submitting an issue to our GitHub Repository.
Please provide us with context that helps us reproduce the problem.

If you can create one, we happily also take a Pull Request with a fix.

## Installing `lexedata` for development

The following steps aren't the one and only solution to go about it, but are reasonable defaults.

 - Make sure you have a Github account and are signed in to Github.
 - Fork `Anaphory/lexedata` (There is a button <a href="/login?return_to=%2FAnaphory%2Flexedata" rel="nofollow" data-hydro-click="{&quot;event_type&quot;:&quot;authentication.click&quot;,&quot;payload&quot;:{&quot;location_in_page&quot;:&quot;repo details fork button&quot;,&quot;repository_id&quot;:288489134,&quot;auth_type&quot;:&quot;LOG_IN&quot;,&quot;originating_url&quot;:&quot;https://github.com/Anaphory/lexedata&quot;,&quot;user_id&quot;:null}}" data-hydro-click-hmac="12434dbbcc05e179b4a260522173eeb34701b04feb5fe23cefd2cd566d7ff52d" aria-label="You must be signed in to fork a repository" data-view-component="true" class="tooltipped tooltipped-s btn-sm btn">  <svg aria-hidden="true" height="16" viewBox="0 0 16 16" version="1.1" width="16" data-view-component="true" class="octicon octicon-repo-forked mr-2"> <path fill-rule="evenodd" d="M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h1.5v2.128a2.251 2.251 0 101.5 0V8.5h1.5a2.25 2.25 0 002.25-2.25v-.878a2.25 2.25 0 10-1.5 0v.878a.75.75 0 01-.75.75h-4.5A.75.75 0 015 6.25v-.878zm3.75 7.378a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm3-8.75a.75.75 0 100-1.5.75.75 0 000 1.5z"></path> </svg>Fork <span id="repo-network-counter" data-pjax-replace="true" title="4" data-view-component="true" class="Counter">4</span> </a> on the top-right)
 - Clone your fork to your local computer, using `git clone git@github.com:YourUserName/lexedata` or one of the available GUI tools.
 - Create a Python virtual environment for Lexedata. If you use Anaconda, this works with `conda create -n lexedata python=3.9 anaconda` (or whatever name and Python version you prefer – there are more details in the Anaconda documentation), and activate it.
 - Navigate inside the Lexedata clone on your machine. Install a development version of `lexedata` and its dependencies using `pip install -e .[dev,test]` and the additional packages useful or necessary for development using `pip install pre-commit tox`.
 - Install the CLDF catalogs CLTS, Glottolog, and Concepticon, as described in the [general Lexedata installation instructions](https://lexedata.readthedocs.io/en/latest/installation.html).
 - Run
   ```
   pre-commit install
   ```
   to make sure that [`black`](https://black.readthedocs.io/en/stable/) and [`flake8`](https://flake8.pycqa.org/en/latest/) are run as git pre-commit hooks, which will ensure the formatting of any changed code you want to contribute in the future.
 - Run
   ```
   tox
   ```
   to run the tests. Tox will install some additional packages into a dedicated virtualenv, which may also be useful for you to have in your general working environment, so you can run specific tests manually instead of the whole testing suite:
    - codecov
    - black ~= 21.6b0
    - flake8
    - flake8-breakpoint
    - pytest
    - pytest-cov
    - mypy
    - scriptdoctest@git+https://git@github.com/Anaphory/scriptdoctest.git

If you want a local version of the documentation, make sure you have `sphinx` installed. Then you can build the documentation by running `make html` (or any other [Sphinx builder](https://www.sphinx-doc.org/en/master/man/sphinx-build.html#cmdoption-sphinx-build-b)).
