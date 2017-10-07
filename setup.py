from os.path import abspath, dirname, join

from setuptools import find_packages, setup
from pip.req import parse_requirements

PACKAGE_NAME = 'turg'
PACKAGE_VERSION = '0.0.1'
DESCRIPTION = 'The Urban Game'

here = abspath(dirname(__file__))
install_reqs = parse_requirements(join(here, 'requirements.txt'), session=False)
reqs = [str(ir.req) for ir in install_reqs]


setup(
    name=PACKAGE_NAME,
    author='ToxicWar',
    description=DESCRIPTION,
    url='https://github.com/ToxicWar/turg',
    license='Apache License',
    install_requires=reqs,
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
)
