import os
import sys
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()

requires = [
    'pyyaml==3.10',
    'python-simple-hipchat==0.1',
]

test_requires = []

if sys.version_info[:3] < (2, 5, 0):
    requires.append('pysqlite')

entry_points = ""

setup(name='plumbago',
      version=0.1,
      description='simple alert system for graphite',
      long_description=README,
      classifiers=[
          "Programming Language :: Python",
          "Framework :: Pyramid",
          ],
      author='Pheed Inc',
      author_email='code@pheed.com',
      url='',
      keywords='graphite hipchat alert monitor',
      packages=find_packages(exclude=['tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=test_requires,
      entry_points=entry_points,
      paster_plugins=['pyramid'],
      )

