import multiprocessing, logging # Fix atexit bug
from setuptools import setup, find_packages


def readme():
    try:
        return open('README.rst').read()
    except:
        pass
    return ''


def version():
    try:
        import re
        return re.search("^__version__ = '(.*)'",
                open('pyconfig/__init__.py').read(), re.M).group(1)
    except:
        raise RuntimeError("Could not get version")


setup(
        name='pyconfig',
        version=version(),
        description="Python-based singleton configuration",
        long_description=readme(),
        author="Jacob Alheid",
        author_email="shakefu@gmail.com",
        url="http://github.com/shakefu/pyconfig",
        packages=find_packages(exclude=['test']),
        test_suite='nose.collector',
        install_requires=[
            'six',
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

