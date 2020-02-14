from setuptools import setup, find_packages

setup(
    name="lexicaldatabase",
    version="0.1",
    description="Tools for editing lexical databases for historical linguistics",
    author="Melvin Steiger, Gereon A. Kaiping",
    author_email="gereon.kaiping@geo.uzh.ch",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    keywords='data linguistics',
    license='???',
    url="https://gitlab.uzh.ch/gereonalexander.kaiping/editinglexicaldatasets",
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    platforms='any',
    install_requires=[
        "attr",
        "openpyxl",
        "pycldf",
        "unidecode"],
    entry_points={
        'console_scripts': [
            'import-data-mg = importer.cells:main',
        ]
    }
)
