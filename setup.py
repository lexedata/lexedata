from setuptools import setup, find_packages
import platform

REQUIRES = [
    "attrs",
    "python-igraph",
    "openpyxl",
    "pycldf",
    "sqlalchemy",
    "segments",
    "pyclts",
    "lingpy",
    "unidecode",
    "cldfbench",
    "pyglottolog",
    "pyconcepticon",
    "pyclts",
]
if platform.system() != 'Windows':
    REQUIRES.append("readline")
else:
    REQUIRES.append("pyreadline")

setup(
    name="lexedata",
    version="0.1",
    description="Tools for editing lexical databases for historical linguistics",
    author="Melvin Steiger, Gereon A. Kaiping",
    author_email="gereon.kaiping@geo.uzh.ch",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="data linguistics",
    license="???",
    url="https://gitlab.uzh.ch/gereonalexander.kaiping/editinglexicaldatasets",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    platforms="any",
    install_requires=REQUIRES,
    entry_points={
        "console_scripts": [
            "import-data-mg = importer.cells:main",
        ]
    },
)
