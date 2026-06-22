import os
import psycopg2
import psycopg2.extras
from flask import g


def get_db():
    if 'db' not in g:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            g.db = psycopg2.connect(database_url, sslmode='require')
        else:
            g.db = psycopg2.connect(
                dbname='k29photo',
                user='adamshawky',
                host='localhost'
            )
        g.db.autocommit = False
    return g.db


def get_cursor():
    return get_db().cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def commit():
    get_db().commit()


def rollback():
    get_db().rollback()


def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()