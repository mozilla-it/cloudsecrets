import os
import setuptools
from setuptools import setup, find_packages

setup(
    name="cloudsecrets",
    version="0.0.1",
    description="Python tool for accessing mozilla cloud secrets",
    python_requires=">=3.4",
    author="Mozilla IT Service Engineering",
    author_email="afrank@mozilla.com",
    packages=find_packages(),
    entry_points={"console_scripts": ["cloud-secrets=cloudsecrets.cli:main",],},
    install_requires=[
        "google-cloud-secret-manager",
        "boto3",
        # Google Cloud's Protocol Buffer requirement
        # https://github.com/grpc/grpc/pull/18408/files#diff-b4ef698db8ca845e5845c4618278f29aR3
        "cython>=0.29.8",
    ],
    extras_require={"test": ["coverage", "pytest"],},
    project_urls={"Source": "https://github.com/mozilla-it/cloudsecrets",},
    test_suite="tests.unit",
)
