
from setuptools import setup, find_packages

setup(name = 'cyclence'
      ,version = '0.1'
      ,packages = find_packages()
      ,author = 'Josh Kuhn'
      ,author_email = 'kuhn.joshua+cyclence@gmail.com'
      ,license = 'AGPL3'
      ,install_requires = ["sqlalchemy",
                           "tornado",
                           "psycopg2",
                           "supervisor"
                           ]
)

