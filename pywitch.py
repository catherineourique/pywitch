from websocket import create_connection
import time
import json
import random
import requests
import threading
import time
from pywitch_tmi import TMI

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

### Auxiliary functions ######################################################


def nonce(length):
    possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    text = ''.join(
        [possible[int(random.random() * len(possible))] for i in range(length)]
    )
    return text


def json_eval(string):
    if not string:
        return {}
    try:
        return json.loads(string)
    except Exception as e:
        return {}


##############################################################################


class PyWitch:
    def __init__(self, token=None, verbose=1):
        self.token = token
        self.verbose = verbose
        self.instances = {}
        self.threads = {}
        self.data = {'tmi': {}, 'rewards': {}, 'heat': {}, 'stream_info': {}}
        self.alive = {}
        self.websockets = {}
        self.users = {}
        self.users_login = {}
        self.kind_functions = {
            #'tmi': [self.connect_tmi, self.event_tmi],
            'heat': [self.connect_heat, self.event_heat],
            'rewards': [self.connect_rewards, self.event_rewards],
            'stream_info': [self.event_stream_info],
        }
        self.callback = {}

        if not (self.token):
            self.log(no_token_msg)
            raise Exception('Token not provided! Terminating.')

        if not hasattr(self, 'validation'):
            self.validate_token()

        self.user = self.get_user_info(
            self.validation['user_id'], wait_for_response=True
        )

    def validate_token(self):
        self.log("Validating token...")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(__validate_token_url__, headers=headers)
        if response.status_code == 200:
            self.validation = response.json()
            self.log("Successfully validated token!")

            self.helix_headers = {
                "Client-ID": self.validation["client_id"],
                "Authorization": f"Bearer {self.token}",
            }

        else:
            self.log(f"Failed to validate token: {response.json()}")
            raise Exception('Failed to validate token.')

    ### Thread management functions ##############################################

    def keep_alive(self, kind, channel):
        functions = self.kind_functions[kind]
        self.alive[kind] = True
        while kind in self.alive and self.alive[kind]:
            for fn in functions:
                fn(channel)

    def start_thread(self, kind, channel):
        thread = threading.Thread(target=self.keep_alive, args=(kind, channel))
        self.threads[kind] = {'thread': thread, 'running': True}
        self.threads[kind]['thread'].start()
        return thread

    def stop_signal_thread(self, kind, channel):
        if not kind in self.threads:
            self.log(f"Invalid thread kind! Returning")
            return False
        self.threads[kind]['running'] = False
        self.threads[kind]['thread'].join()
        self.threads.pop(kind)

    def stop_signal_all_threads(self):
        kinds = list(self.threads.keys())
        for kind in kinds:
            self.stop_signal_thread(kind)

    ##############################################################################

    ### Connection functions #####################################################

    def connect_rewards(self, channel):
        try:
            kind = 'rewards'
            user_id = self.validation['user_id']
            ws = create_connection("wss://pubsub-edge.twitch.tv")
            ws.send(json.dumps({'type': 'PING'}))
            data = {
                'type': "LISTEN",
                'nonce': nonce(15),
                'data': {
                    'topics': [f'channel-points-channel-v1.{user_id}'],
                    'auth_token': f'{self.token}',
                },
            }
            ws.send(json.dumps(data))
            self.websockets[kind] = ws
            return ws
        except:
            return None

    def connect_heat(self, channel):
        try:
            kind = 'heat'
            user_id = self.validation['user_id']
            ws = create_connection(f"wss://heat-api.j38.net/channel/{user_id}")
            self.websockets[kind] = ws
            return ws
        except:
            return None

    ##############################################################################

    ### Event catch functions ####################################################

    def event_rewards(self, channel):
        try:
            kind = 'rewards'
            ws = self.websockets[kind]
            while self.threads[kind]['running']:
                event = ws.recv()
                event_json = json_eval(event)
                event_time = time.time()
                event_data = event_json.get('data', {})
                event_message = json_eval(event_data.get('message', ''))
                event_msgdata = event_message.get('data', {})
                event_redemption = event_msgdata.get('redemption', {})
                event_reward = event_redemption.get('reward', {})
                event_user = event_redemption.get('user', {})
                event_global_cooldown = event_reward.get('global_cooldown', {})
                event_cooldown_seconds = event_global_cooldown.get(
                    'global_cooldown_seconds'
                )
                event_cooldown_expires_at = event_reward.get(
                    'cooldown_expires_at'
                )
                self.data[kind] = {
                    'type': event_json.get('type'),
                    'data': event_data,
                    'login': event_user.get('login'),
                    'display_name': event_user.get('display_name'),
                    'title': event_reward.get('title'),
                    'prompt': event_reward.get('prompt'),
                    'cost': event_reward.get('cost'),
                    'user_input': event_redemption.get('user_input'),
                    'cooldown': event_cooldown_seconds,
                    'message': event_message,
                    'event_dict': event_json,
                    'event_time': event_time,
                    'event_raw': event,
                }

                event_callback = self.callback.get(kind)
                if event_callback and callable(event_callback):
                    event_callback(self.data[kind])
        except:
            return

    def event_heat(self, channel):
        try:
            kind = 'heat'
            ws = self.websockets[kind]
            while self.threads[kind]['running']:
                event = ws.recv()
                event_data = json_eval(event)
                event_user = str(event_data.get('id'))
                event_display_name = 'NONE'
                event_login = 'NONE'
                if event_user:
                    user_info = self.get_user_info(
                        user_id=event_user, wait_for_response=False
                    )
                    event_display_name = user_info.get('display_name')
                    event_login = user_info.get('login')
                if event_login == 'PYWITCH_LOADING':
                    return

                self.data[kind] = {
                    'type': event_data.get('type'),
                    'message': event_data.get('message'),
                    'x': event_data.get('x'),
                    'y': event_data.get('y'),
                    'type': event_data.get('type'),
                    'display_name': event_display_name,
                    'event_login': event_login,
                    'user_id': event_user,
                    'event_raw': event,
                }
                event_callback = self.callback.get(kind)
                if callable(event_callback):
                    event_callback(self.data[kind])
        except:
            return

    def event_stream_info(self, channel):
        try:
            kind = 'stream_info'
            while self.threads[kind]['running']:
                request_thread = threading.Thread(
                    target=self.get_stream_info, args=(kind,)
                )
                request_thread.start()
                if self.wait_for_response:
                    request_thread.join()
                time.sleep(self.stream_info_interval)
        except:
            return

    ##############################################################################

    ### Request functions #########################################################

    def request_stream_info(self, kind):
        user_id = self.validation['user_id']
        response = requests.get(
            f'https://api.twitch.tv/helix/streams',
            headers=self.helix_headers,
            params={'user_id': user_id},
        )
        if response.status_code == 200:
            data = response.json()
            data = data.get('data', [])
            data = data and data[0] or {}
            if self.data['stream_info'] == data:
                return
            self.data['stream_info'] = data
            event_callback = self.callback.get(kind)
            if callable(event_callback):
                event_callback(self.data[kind])

    def request_user_info(self, user_id=None, login=None):
        if not (user_id or login):
            return
        if user_id:
            params = {'id': user_id}
        if login:
            params = {'login': login}

        response = requests.get(
            f'https://api.twitch.tv/helix/users',
            headers=self.helix_headers,
            params=params,
        )
        if response.status_code == 200:
            data = response.json()
            data = data.get('data', [])
            data = data and data[0] or {}
            response_user_id = data.get('id')
            response_display_name = data.get('display_name')
            response_login = data.get('login')
            self.users[response_user_id] = {
                'login': response_login,
                'user_id': response_user_id,
                'display_name': response_display_name,
            }
            self.users_login[response_login] = response_user_id
        else:
            self.users.pop(user_id)

    ##############################################################################

    ### Start functions ##########################################################

    def start_tmi(self, channel, callback=None):
        self.instances['tmi'] = TMI(self, channel, callback)
        self.instances['tmi'].start_thread()
        return self.instances['tmi']

    def start_rewards(self, channel, callback=None):
        self.set_event_callback('rewards', callback)
        self.start_thread('rewards', channel)

    def start_heat(self, channel, callback=None):
        self.set_event_callback('heat', callback)
        self.start_thread('heat', channel)

    def start_stream_info(self, channel, callback=None, interval=5):
        self.stream_info_interval = interval
        self.set_event_callback('stream_info', callback)
        self.start_thread('stream_info', channel)

    ##############################################################################

    ### Auxiliary object functions ###############################################

    def set_event_callback(self, kind, callback):
        if not kind in self.data:
            raise Exception("Invalid data kind! Terminating.")
        if not callable(callback) and callback != None:
            raise Exception("Provided callback is not callable! Terminating.")
        self.callback[kind] = callback

    def get_user_info(self, user_id=None, login=None, wait_for_response=True):
        if user_id:
            user_id = str(user_id)
        if login:
            user_id = self.users_login.get(login)
        default = {
            'login': 'PYWITCH_LOADING',
            'user_id': 'PYWITCH_LOADING',
            'display_name': 'PYWITCH_LOADING',
        }
        if not user_id in self.users:
            request_thread = threading.Thread(
                target=self.request_user_info,
                kwargs={'user_id': user_id, 'login': login},
            )
            request_thread.start()
            if wait_for_response:
                request_thread.join()
                if login:
                    user_id = self.users_login.get(login)

        return self.users.get(user_id, default)

    def log(self, msg, level=1):
        if self.verbose >= level:
            print(f'(PyWitch) {msg}')


##############################################################################
