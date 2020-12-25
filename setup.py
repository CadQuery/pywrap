from setuptools import setup

setup(
    name='pywrap',
    version="0.1dev",
    entry_points={'console_scripts': 'pywrap = bindgen.__main__:main'},
    packages=['bindgen'],
    include_package_data = True,
    install_requires=[
        'click',
        'logzero',
        'path.py',
        'clang',
        'cymbal',
        'toml',
        'pandas',
        'joblib',
        'tqdm',
        'jinja2',
        'toposort',
        'pyparsing',
        'pybind11',
        'schema'
    ]
)
