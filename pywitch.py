import asyncio
import time
import websockets
import json
import random
import requests
import threading
import time

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


def get_display_name(string):
    try:
        ipos = string.find('display-name') + 13
        fpos = string.find(';', ipos)
        return string[ipos:fpos]
    except:
        return ''


def get_user_id(string):
    try:
        ipos = string.find('user-id') + 8
        fpos = string.find(';', ipos)
        return string[ipos:fpos]
    except:
        return ''


def get_privmsg(string):
    try:
        ipos = string.find('PRIVMSG')
        ipos = string.find(':', ipos) + 1
        fpos = string.find('\r\n', ipos)
        return string[ipos:fpos]
    except:
        return ''


def json_eval(string):
    if not string:
        return {}
    try:
        return json.loads(string)
    except Exception as e:
        return {}

##############################################################################

class PyWitch:
    def __init__(self, channel, token=None, wait_for_response=True, verbose=1):
        self.channel = channel
        self.token = token
        self.wait_for_response = wait_for_response
        self.verbose = verbose
        self.threads = {}
        self.data = {'tmi': {}, 'rewards': {}, 'heat': {}, 'stream_info': {}}
        self.users = {}
        self.thread_kind = {
            'tmi': self.thread_tmi,
            'heat': self.thread_heat,
            'rewards': self.thread_rewards,
            'stream_info': self.thread_stream_info,
        }
        self.callback = {}

        if not (self.token):
            self.log(no_token_msg)
            raise Exception('Token not provided! Terminating.')
            
        if not hasattr(self, 'validation'):
            self.validate_token()

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

    def start_thread(self, kind, is_async=True):
        if not kind in self.thread_kind:
            self.log(f"Invalid thread kind! Returning")
            return False
        if not hasattr(self, 'validation'):
            self.validate_token()
        if is_async:
            thread = threading.Thread(target=self.start_async, args=(kind,))
        else:
            thread = threading.Thread(target=self.thread_kind[kind], args=())
        self.threads[kind] = {'thread': thread, 'running': True}
        self.threads[kind]['thread'].start()
        return thread

    def stop_signal_thread(self, kind):
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

    def start_async(self, kind):
        while self.threads[kind]['running']:
            self.thread_kind[kind]
            asyncio.run(self.thread_kind[kind]())
            
##############################################################################

### Thread functions #########################################################


    async def thread_tmi(self):
        try:
            kind = 'tmi'
            async with websockets.connect(
                "wss://irc-ws.chat.twitch.tv:443"
            ) as websocket:
                cap = 'twitch.tv/tags twitch.tv/commands twitch.tv/membership'
                await websocket.send(f'CAP REQ : {cap}')
                await websocket.send(f'PASS oauth:{self.token}')
                await websocket.send(f'NICK {self.channel}')
                await websocket.send(f'JOIN #{self.channel}')
                while self.threads[kind]['running']:
                    event = await websocket.recv()
                    if not 'PRIVMSG' in event:
                        continue
                    event_time = time.time()
                    display_name = get_display_name(event)
                    user_id = get_user_id(event)
                    if not user_id in self.users:
                        self.users[user_id] = {
                            'display_name': display_name,
                        }
                    message = get_privmsg(event)
                    self.data[kind] = {
                        'display_name': display_name,
                        'event_time': event_time,
                        'user_id': user_id,
                        'message': message,
                        'event_raw': event,
                    }
                    event_callback = self.callback.get(kind)
                    if callable(event_callback):
                        event_callback(self.data[kind])
        except:
            return

    async def thread_rewards(self):
        try:
            kind = 'rewards'
            user_id = self.validation['user_id']
            async with websockets.connect(
                "wss://pubsub-edge.twitch.tv"
            ) as websocket:

                await websocket.send(json.dumps({'type': 'PING'}))
                data = {
                    'type': "LISTEN",
                    'nonce': nonce(15),
                    'data': {
                        'topics': [f'channel-points-channel-v1.{user_id}'],
                        'auth_token': f'{self.token}',
                    },
                }
                await websocket.send(json.dumps(data))
                while self.threads[kind]['running']:
                    event = await websocket.recv()
                    event_json = json_eval(event)
                    event_time = time.time()
                    event_data = event_json.get('data', {})
                    event_message = json_eval(event_data.get('message', ''))
                    event_msgdata = event_message.get('data', {})
                    event_redemption = event_msgdata.get('redemption', {})
                    event_reward = event_redemption.get('reward', {})
                    event_user = event_redemption.get('user', {})
                    event_global_cooldown = event_reward.get(
                        'global_cooldown', {}
                    )
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
                    if callable(event_callback):
                        event_callback(self.data[kind])

        except Exception as e:
            print(e)
            return

    async def thread_heat(self):
        try:
            kind = 'heat'
            user_id = self.validation['user_id']
            async with websockets.connect(
                f"wss://heat-api.j38.net/channel/{user_id}"
            ) as websocket:

                while self.threads[kind]['running']:
                    event = await websocket.recv()
                    event_data = json_eval(event)
                    event_user = str(event_data.get('id'))
                    event_display_name = 'NONE'
                    event_login = 'NONE'
                    if event_user:
                        user_info = self.get_user_info_by_id(event_user)
                        event_display_name = user_info.get('display_name')
                        event_login = user_info.get('login')

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

        except Exception as e:
            print(e)
            return
            
    def thread_stream_info(self):
        kind = 'stream_info'
        while self.threads[kind]['running']:
            request_thread = threading.Thread(
                target=self.get_stream_info, args=(kind,)
            )
            request_thread.start()
            if self.wait_for_response:
                request_thread.join()
            time.sleep(self.stream_info_interval)
            
    def get_stream_info(self, kind):
        user_id = self.validation['user_id']
        response = requests.get(
            f'https://api.twitch.tv/helix/streams',
            headers=self.helix_headers,
            params = {'user_id': user_id},
        )
        if response.status_code == 200:
            data = response.json()
            data = data.get('data',[])
            data = data and data[0] or {}
            if self.data['stream_info'] == data:
                return
            self.data['stream_info'] = data
            event_callback = self.callback.get(kind)
            if callable(event_callback):
                event_callback(self.data[kind])
            
##############################################################################

### Start functions ##########################################################

    def start_tmi(self, callback = None):
        self.set_event_callback('tmi', callback)
        self.start_thread('tmi')

    def start_rewards(self, callback = None):
        self.set_event_callback('rewards', callback)
        self.start_thread('rewards')

    def start_heat(self, callback = None):
        self.set_event_callback('heat', callback)
        self.start_thread('heat')
        
    def start_stream_info(self, callback = None, interval = 5):
        self.stream_info_interval = interval
        self.set_event_callback('stream_info', callback)
        self.start_thread('stream_info')
        
##############################################################################

### Auxiliary object functions ###############################################

    def set_event_callback(self, kind, callback):
        if not kind in self.data:
            raise Exception("Invalid data kind! Terminating.")
        if not callable(callback) and callback != None:
            raise Exception("Provided callback is not callable! Terminating.")
        self.callback[kind] = callback

    def get_user_info_by_id(self, user_id):
        default = {
            'display_name': 'PYWITCH_LOADING',
            'login': 'PYWITCH_LOADING',
        }
        if not user_id in self.users:
            self.users[user_id] = default
            request_thread = threading.Thread(
                target=self.get_user_info_by_id_thread, args=(user_id,)
            )
            request_thread.start()
            if self.wait_for_response:
                request_thread.join()
        return self.users.get(user_id, default)

    def get_user_info_by_id_thread(self, user_id):

        response = requests.get(
            f'https://api.twitch.tv/helix/channels',
            headers = self.helix_headers,
            params = {'broadcaster_id': user_id}
        )
        if response.status_code == 200:
            data = response.json()
            data = data.get('data',[])
            data = data and data[0] or {}
            self.users[user_id]['display_name'] = data.get('broadcaster_name')
            self.users[user_id]['login'] = data.get('broadcaster_name')
        else:
            self.users.pop(user_id)

    def log(self, msg, level=1):
        if self.verbose >= level:
            print(f'(PyWitch) {msg}')
            
##############################################################################
