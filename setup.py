"""A setuptools based setup module for agilepoint"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from distutils.command.install import INSTALL_SCHEMES
# To use a consistent encoding
from codecs import open
from os import path

for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

name = 'aws_lambda'
version_file = open(path.join(name, 'VERSION'))
version = version_file.read().strip()
setup(
    name=name,
    version=version,
    description='Set of utilities to include across AWS Lambda functions',
    long_description=long_description,
    url='https://github.com/blade2005/aws_lambda_tools',
    author='Craig Davis',
    author_email='cdavis@stoneydavis.com',
    license='GPLv3',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='aws lambda',
    packages=find_packages(),
    install_requires=['ConfigParser'],
    extras_require={},
    package_data={},
    data_files=[],
    entry_points={},
    scripts=[],
)
