import time
import json
import requests

__validate_token_url__ = 'https://id.twitch.tv/oauth2/validate'
__pywitch_client_id__ = 'l2o6fudb8tq6394phgudstdzlouo9n'

get_token_url = (
    'https://id.twitch.tv/oauth2/authorize?'
    'response_type=token&'
    f'client_id={__pywitch_client_id__}&'
    'redirect_uri=https://localhost&'
    'scope=channel:manage:redemptions%20channel:read:redemptions%20'
    'user:read:email%20chat:edit%20chat:read'
)

response_token_url = (
    'https://localhost/#access_token=YOUR_ACCESS_TOKEN&'
    'scope=channel%3Amanage%3Aredemptions+channel%3Aread%3Aredemptions+user%'
    '3Aread%3Aemail+chat%3Aedit+chat%3Aread&token_type=bearer'
)

no_token_msg = f"""ERROR: No token provided!

To generate token, you need to authenticate PyWitch application in the
following URL:
{get_token_url}

NOTE: This URL will provide the following scopes to PyWitch application:
[channel:manage:redemptions, channel:read:redemptions, user:read:email,
chat:edit, chat:read]

It will ask for you to login in your Twitch Account to authorize. After
authorizing it, it will redirect to an (usually) broken page. The only thing
you need from the page is its URL. Copy that URL, it should look like this:
{response_token_url}

Your token is what is filling YOUR_ACCESS_TOKEN from the URL. 

Alternatively, you can create a Twitch Application in the
following URL:
https://dev.twitch.tv

To do so, first login with your Twitch Account, click "Your Console", then 
"Applications" and "Register Your Application".
Give it a pretty name and set OAuth Redirect URLs as "https://localhost", and
set Category to any of the given options.
After that, your application will receive an "Client ID", keep that in hands.

Now you need to access the following URL, replacing {__pywitch_client_id__}
with your application client_id:
{get_token_url}
"""


def json_eval(string):
    if not string:
        return {}
    try:
        return json.loads(string)
    except Exception as e:
        return {}


def pywitch_log(msg, verbose=False):
    if verbose:
        print(f'(PyWitch) {msg}')


def validate_token(token=None, verbose=True):
    if not token:
        pywitch_log(no_token_msg, verbose)
        raise Exception('Token not provided! Terminating.')
    pywitch_log("Validating token...", verbose)
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(__validate_token_url__, headers=headers)
    if response.status_code == 200:
        validation = response.json()
        pywitch_log("Successfully validated token!", verbose)

        helix_headers = {
            "Client-ID": validation["client_id"],
            "Authorization": f"Bearer {token}",
        }
        return validation, helix_headers

    else:
        pywitch_log(f"Failed to validate token: {response.json()}", verbose)
        raise Exception('Failed to validate token.')


def validate_callback(callback):
    if not callable(callback) and callback != None:
        raise Exception("Provided callback is not callable! Terminating.")


def get_user_info(user_id=None, login=None, helix_headers={}):
    if not (user_id or login):
        return
    if user_id:
        params = {'id': user_id}
    if login:
        params = {'login': login}

    response = requests.get(
        f'https://api.twitch.tv/helix/users',
        headers=helix_headers,
        params=params,
    )
    if response.status_code == 200:
        data = response.json()
        data = data.get('data', [])
        data = data and data[0] or {}
        response_user_id = data.get('id')
        response_display_name = data.get('display_name')
        response_login = data.get('login')
        return {
            'login': response_login,
            'user_id': response_user_id,
            'display_name': response_display_name,
        }
    return {}


def run_forever():
    while True:
        time.sleep(60)
