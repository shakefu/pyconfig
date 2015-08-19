import multiprocessing, logging # Fix atexit bug
from setuptools import setup, find_packages

import pyconfig


setup(
        name='pyconfig',
        version=pyconfig.__version__,
        description="Python-based singleton configuration",
        author="Jacob Alheid",
        author_email="shakefu@gmail.com",
        url="http://github.com/shakefu/pyconfig",
        packages=find_packages(exclude=['test']),
        test_suite='nose.collector',
        install_requires=[
            'pytool',
            ],
        tests_require=[
            'nose',
            'coverage',
            'mock',
            ],
        extras_require={
            'etcd': ['python-etcd']
            },
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
            'Programming Language :: Python :: 3.2',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Utilities',
            ],
        )

