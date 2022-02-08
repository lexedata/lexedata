from setuptools import setup
import platform

if platform.system() == "Windows":
    readline = "pyreadline"
elif platform.system() == "Darwin":
    readline = "gnureadline"
else:
    readline = "readline"

setup(
    extras_require={
        "formatguesser": [readline],
        "test": ["tox"],
        "dev": ["pre-commit"],
    }
)
