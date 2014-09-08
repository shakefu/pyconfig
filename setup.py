import multiprocessing, logging # Fix atexit bug
from setuptools import setup, find_packages

import pyconfig


setup(
        name='pyconfig',
        version=pyconfig.__version__,
        description="Python-based singleton configuration",
        author="Jacob Alheid",
        author_email="jake@team.about.me",
        url="http://github.com/aol/pyconfig",
        packages=find_packages(exclude=['test']),
        test_suite='nose.collector',
        tests_require=[
            'nose',
            'coverage',
            'mock',
            ],
        entry_points={
            'console_scripts':[
                'pyconfig = pyconfig.scripts:main',
                ],
            },
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 2.6',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Utilities',
            ],
        )

