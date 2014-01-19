from setuptools import setup

setup(
        name='test2',
        version='1.0.0',
        py_modules=['test2'],
        entry_points={
            'pyconfig':['any = test2'],
                }
        )
