# Copyright (C) 2024 twyleg
import versioneer
from pathlib import Path
from setuptools import find_packages, setup


def read(relative_filepath):
    return open(Path(__file__).parent / relative_filepath).read()


def read_long_description() -> str:
    return read("README.md")


setup(
    name="classroom_utils",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="Torsten Wylegala",
    author_email="mail@twyleg.de",
    description="Utilities to handle stuff likes github orgs for classes.",
    license="GPL 3.0",
    keywords="class classroom github edu education",
    url="https://github.com/twyleg/classroom_utils",
    packages=find_packages(),
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    include_package_data=True,
    install_requires=[
        "jsonschema",
        "PyGithub",
        "GitPython"
    ],
    entry_points={
        "console_scripts": [
            "classroom_utils = classroom_utils.main:main",
        ]
    },
)
