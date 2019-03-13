""" Database GINO models """

# pylint: disable=maybe-no-member

from gino.ext.tornado import Gino

DB = Gino()

class Candidate(DB.Model):
    """ Candidate for vacancy model """

    __tablename__ = 'candidates'

    id = DB.Column(DB.Integer())

    first_name = DB.Column(DB.String())
    last_name = DB.Column(DB.String())

    __table_args__ = (DB.UniqueConstraint('id'))

class Inerview(DB.Model):
    """ Interview event model """

    __tablename__ = 'inerviews'

    id = DB.Column(DB.Integer(), primary_key=True, autoincrement=True)

    created = DB.Column(DB.DateTime())
    type = DB.Column(DB.String())

    candidate = DB.Column(DB.Integer(), DB.ForeignKey('candidates.id'))

    start = DB.Column(DB.DateTime())
    end = DB.Column(DB.DateTime())

    __table_args__ = (DB.UniqueConstraint('id'))

async def gino_run(**kwargs):
    """ Set up connection to the database """

    postgres_url = 'postgresql://{username}:{password}@{hostname}:{port}/{dbname}'

    await DB.set_bind(postgres_url.format(**kwargs))
