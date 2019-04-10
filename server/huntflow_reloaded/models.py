""" Database GINO models """

from gino.ext.tornado import Gino

DB = Gino()

class Candidate(DB.Model):
    """ Candidate for vacancy model """

    __tablename__ = 'candidates'

    id = DB.Column(DB.Integer())  # pylint: disable=maybe-no-member

    first_name = DB.Column(DB.String())  # pylint: disable=maybe-no-member
    last_name = DB.Column(DB.String())  # pylint: disable=maybe-no-member

    __table_args__ = (DB.UniqueConstraint('id'))  # pylint: disable=maybe-no-member

class Interview(DB.Model):
    """ Interview event model """

    __tablename__ = 'interviews'

    id = DB.Column(DB.Integer(), primary_key=True, autoincrement=True)  # pylint: disable=maybe-no-member

    created = DB.Column(DB.DateTime())  # pylint: disable=maybe-no-member
    type = DB.Column(DB.String())  # pylint: disable=maybe-no-member

    candidate = DB.Column(DB.Integer(), DB.ForeignKey('candidates.id'))  # pylint: disable=maybe-no-member

    start = DB.Column(DB.DateTime())  # pylint: disable=maybe-no-member
    end = DB.Column(DB.DateTime())  # pylint: disable=maybe-no-member

    __table_args__ = (DB.UniqueConstraint('id'))  # pylint: disable=maybe-no-member

async def gino_run(**kwargs):
    """ Set up connection to the database """

    postgres_url = 'postgresql://{username}:{password}@{hostname}:{port}/{dbname}'

    await DB.set_bind(postgres_url.format(**kwargs))
