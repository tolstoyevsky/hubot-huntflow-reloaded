""" JWT module """

import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

import jwt

DEFAULT_SECRET_KEY = 'secret'
DEFAULT_ACCESS_TOKEN_LIFETIME = '1'
DEFAULT_FESRESH_TOKEN_LIFETIME = '60'

# Define the environment variables when the tornado/testing.py is called.
if sys.argv[0].split('/')[-1] == 'testing.py':
    os.environ['ACCESS_TOKEN_LIFETIME'] = '0.5'
    os.environ['REFRESH_TOKEN_LIFETIME'] = '1'
    os.environ['SECRET_KEY'] = DEFAULT_SECRET_KEY


class ExpiredTokenException(Exception):
    """Exception raised when token is expired. """

class InvalidTokenException(Exception):
    """Exception raised when token is not valid. """

class Token():
    """Abstract class for the token instance. """

    token_type = None
    lifetime = None

    def __init__(self, token=None):
        self.token = token
        self.current_time = datetime.now()

        self.secret = os.getenv('SECRET_KEY', DEFAULT_SECRET_KEY)
        if token is not None:
            self.decode(token)
        else:
            self.payload = {'token-type': self.token_type}
            self.payload['jti'] = uuid4().hex
            self.payload['exp'] = self.current_time + timedelta(
                minutes=float(self.lifetime))

    def decode(self, token):
        """Decodes the given token. """

        try:
            self.payload = jwt.decode(token, self.secret, algorithms='HS256')
        except jwt.ExpiredSignatureError:
            raise ExpiredTokenException

        except (jwt.InvalidSignatureError, jwt.DecodeError):
            raise InvalidTokenException

        exp_datetime = datetime.utcfromtimestamp(self.payload['exp'])

        if exp_datetime < self.current_time:
            raise ExpiredTokenException

    @classmethod
    def for_user(cls, user_id):
        """
        Returns an authorization token for the given user that will be provided
        after authenticating the user's credentials.
        """

        token = cls()
        token.payload['user_id'] = user_id

        return token

    def __str__(self):
        token = jwt.encode(self.payload, self.secret, algorithm='HS256')
        return token.decode('utf-8')


class AccessToken(Token):
    """Class implementing access token instance. """

    token_type = 'access'
    lifetime = os.getenv('ACCESS_TOKEN_LIFETIME', DEFAULT_ACCESS_TOKEN_LIFETIME)


class RefreshToken(Token):
    """Class implementing refresh token instance. """

    token_type = 'refresh'
    lifetime = os.getenv('REFRESH_TOKEN_LIFETIME', DEFAULT_FESRESH_TOKEN_LIFETIME)
    no_copy_claims = ('token-type', 'exp', 'jti')

    def access_token(self):
        """
        Returns an access token created from this refresh token.
        """
        access = AccessToken()

        access.payload['exp'] = self.current_time + timedelta(
            minutes=float(access.lifetime))

        no_copy = self.no_copy_claims
        for claim, value in self.payload.items():
            if claim in no_copy:
                continue
            access.payload[claim] = value

        return access
