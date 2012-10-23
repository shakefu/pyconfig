import multiprocessing, logging # Fix atexit bug
import os
from setuptools import setup, find_packages


def README():
    try:
        return open(os.path.join(os.path.dirname(__file__),
            'README')).read()
    except:
        pass


setup(
        name='pyconfig',
        version='1.1.1',
        description="Python-based singleton configuration",
        long_description=README(),
        author="Jacob Alheid",
        author_email="jake@about.me",
        url="http://github.com/shakefu/pyconfig",
        py_modules=['pyconfig'],
        test_suite='nose.collector',
        tests_require=[
            'nose',
            'coverage',
            'mock',
            ],
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Programming Language :: Python :: 2.7',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Utilities',
            ],
        )

