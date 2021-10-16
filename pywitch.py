import asyncio
import pytmi
import time
import websockets
import json
import random
import requests

__validate_token_url__ = 'https://id.twitch.tv/oauth2/validate'

get_token_url = (
    'https://id.twitch.tv/oauth2/authorize?'
    'response_type=token&'
    'client_id=YOUR_CLIENT_ID&'
    'redirect_uri=http://localhost&'
    'scope=channel:manage:redemptions channel:read:redemptions '
    'user:read:email chat:edit chat:read'
)

response_token_url = (
    'http://localhost/#access_token=YOUR_ACCESS_TOKEN&'
    'scope=channel%3Amanage%3Aredemptions+channel%3Aread%3Aredemptions+user%'
    '3Aread%3Aemail+chat%3Aedit+chat%3Aread&token_type=bearer'
)

no_token_msg = f"""ERROR: No token provided!

To generate token, you first need to create a Twitch Application in the
following URL:
https://dev.twitch.tv

Login with your Twitch Account, click "Your Console", then "Applications" and
"Register Your Application".
Give it a pretty name and set OAuth Redirect URLs as "http://localhost", and
set Category to any of the given options.
After that, your application will receive an "Client ID", keep that in hands.

Now you need to access the following URL with your "Client ID" in your
browser:
{get_token_url}

It will ask for you to login in your Twitch Account to authorize. After
authorizing it, it will redirect to an (usually) broken page. The only thing
you need from the page is its URL. Copy that URL, it should look like this:
{response_token_url}

Your token is what is filling YOUR_ACCESS_TOKEN from the URL. 
"""


def nonce(length):
    possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    text = ''.join(
        [possible[int(random.random() * len(possible))] for i in range(length)]
    )
    return text


class PyWitch:
    def __init__(self, channel, token=None, verbose=1):
        self.channel = channel
        self.token = token
        self.verbose = verbose

        if not (self.token):
            self.log(no_token_msg)
            raise Exception('Token not provided! Terminating')

    def validate_token(self):
        self.log("Validating token...")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(__validate_token_url__, headers=headers)
        if response.status_code == 200:
            self.validation = response.json()
            self.log(" Successfully validated token!")
        else:
            self.log(f"Failed to validate token: {response.json()}")
            raise Exception('Failed to validate token')

    def log(self, msg, level=1):
        if self.verbose >= level:
            print(f'(PyWitch) {msg}')
