import os
from distutils.core import setup

setup(
    name="flatsurvey",
    version="0.1.0",
    packages=[
        "flatsurvey",
        "flatsurvey.cache",
        "flatsurvey.jobs",
        "flatsurvey.pipeline",
        "flatsurvey.aws",
        "flatsurvey.surfaces",
        "flatsurvey.reporting",
        "flatsurvey.worker",
        "flatsurvey.cache",
        "flatsurvey.ui",
        "flatsurvey.test",
    ],
    license="GPL 3.0+",
    long_description=open("README.md").read(),
    include_package_data=True,
    install_requires=[
        "pinject",
    ],
    entry_points={
        "console_scripts": [
            "flatsurvey=flatsurvey.survey:survey",
            "flatsurvey-worker=flatsurvey.worker.worker:worker",
            "flatsurvey-maintenance=flatsurvey.cache.maintenance:cli",
        ],
    },
    package_data={
        "flatsurvey.aws": ["*.graphql"],
    },
)
