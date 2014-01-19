from setuptools import setup

setup(
        name='test1',
        version='1.0.0',
        py_modules=['test1'],
        entry_points={
            'pyconfig':['any = test1'],
                }
        )
