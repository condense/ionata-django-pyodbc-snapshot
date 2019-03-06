#!/usr/bin/env python

from distutils.core import setup

setup(name='django-pyodbc-mssql',
      version='1.0-ionata1',
      description='Django MS SQL Server backends using pyodbc',
      author='django-pyodbc team',
      url='http://code.google.com/p/django-pyodbc',
      packages=['sql_server', 'sql_server.pyodbc', 'sql_server.extra'],
     )
