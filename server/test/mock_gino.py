""" GINO Mocks for tests """

from sys import stderr

DATABASE = []

def logging(text):
    """ Stderr output """
    prefix = '[ GINO MOCK ]'
    stderr.write('%s %s \n' % (prefix, text))

class gino:  # pylint: disable=invalid-name,too-few-public-methods
    """ Class for asynchronous queries """
    @staticmethod
    async def all():
        """ Getting all records """
        return DATABASE

class query:  # pylint: disable=invalid-name,too-few-public-methods
    """ Class for database queries """

    gino = gino

    @staticmethod
    def where(conditional):
        """ Filter query """
        logging('where conditional %s' % conditional)
        return query

class Model:  # pylint: disable=too-few-public-methods
    """ GINO Model class """

    query = query

    @staticmethod
    async def create(**options):
        """ Creating new record """
        DATABASE.append(options)
        return options

class Gino:
    """ GINO class mock """
    Model = Model

    def Column(self, *args, primary_key=False, autoincrement=False):  # pylint: disable=invalid-name,no-self-use
        """ db.Column replacement """
        options = [
            ', '.join(args),
            'primary_key' if primary_key else '',
            'autoincrement' if autoincrement else ''
        ]
        logging('New Column %s' % ' '.join(options))
        return [x for x in args]

    async def set_bind(self, url):
        """ Simulation of connecting to database """
        logging('Connection to database "%s"' % url)

    # Fields
    def String(self):  # pylint: disable=invalid-name,no-self-use
        """ String field """
        return 'String'
    def Integer(self):  # pylint: disable=invalid-name,no-self-use
        """ Integer field """
        return 'Integer'
    def DateTime(self):  # pylint: disable=invalid-name,no-self-use
        """ Datetime field """
        return 'DateTime'
    def ForeignKey(self, relation):  # pylint: disable=invalid-name,no-self-use
        """ Related field """
        return 'ForeignKey %s' % relation

    def UniqueConstraint(self, param):  # pylint: disable=invalid-name,no-self-use
        """ Unique parameter declaration """
        return 'UniqueConstraint %s' % param
