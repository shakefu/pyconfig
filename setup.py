from setuptools import setup, find_packages

setup(
        name='pyconfig',
        version='0.1.0-dev',
        description="Python-based singleton configuration",
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
        )

