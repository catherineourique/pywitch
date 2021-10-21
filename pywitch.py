import asyncio
import time
import websockets
import json
import random
import requests
import threading

__validate_token_url__ = 'https://id.twitch.tv/oauth2/validate'
__pywitch_client_id__ = 'l2o6fudb8tq6394phgudstdzlouo9n'

get_token_url = (
    'https://id.twitch.tv/oauth2/authorize?'
    'response_type=token&'
    f'client_id={__pywitch_client_id__}&'
    'redirect_uri=http://localhost&'
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


class PyWitch:
    def __init__(self, channel, token=None, verbose=1):
        self.channel = channel
        self.token = token
        self.verbose = verbose
        self.threads = {}
        self.data = {'tmi': {}, 'rewards': {}}
        self.thread_kind = {
            'tmi': self.thread_tmi,
            'rewards': self.thread_rewards
        }

        if not (self.token):
            self.log(no_token_msg)
            raise Exception('Token not provided! Terminating')

    def validate_token(self):
        self.log("Validating token...")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(__validate_token_url__, headers=headers)
        if response.status_code == 200:
            self.validation = response.json()
            self.log("Successfully validated token!")
        else:
            self.log(f"Failed to validate token: {response.json()}")
            raise Exception('Failed to validate token')

    def start_thread(self, kind):
        if not kind in self.thread_kind:
            self.log(f"Invalid thread kind! Returning")
            return False
        thread = threading.Thread(target=self.start_async, args=(kind,))
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
                    event_time = time.time()
                    display_name = get_display_name(event)
                    message = get_privmsg(event)
                    self.data[kind] = {
                        'display_name': display_name,
                        'event_time': event_time,
                        'message': message,
                        'event_raw': event,
                    }
        except:
            return
            
    async def thread_rewards(self):
        try:
            kind = 'rewards'
            user_id = self.validation['user_id']
            async with websockets.connect(
                "wss://pubsub-edge.twitch.tv"
            ) as websocket:

                await websocket.send(json.dumps({ 'type': 'PING' }))
                data={
                    'type': "LISTEN",
                    'nonce': nonce(15),
                    'data': {
                        'topics': [ f'channel-points-channel-v1.{user_id}' ],
                        'auth_token': f'{self.token}'
                    }
                }
                await websocket.send(json.dumps(data))
                while self.threads[kind]['running']:
                    event = await websocket.recv()
                    event_json = json_eval(event)
                    event_time = time.time()
                    event_data = event_json.get('data',{})
                    event_message = json_eval(event_data.get('message',''))
                    event_msgdata = event_message.get('data',{})
                    event_redemption = event_msgdata.get('redemption',{})
                    event_reward = event_redemption.get('reward', {})
                    event_user = event_redemption.get('user',{})
                    event_global_cooldown = event_reward.get(
                        'global_cooldown', {}
                    )
                    event_cooldown_seconds = event_global_cooldown.get(
                        'global_cooldown_seconds'
                    )
                    event_cooldown_expires_at=event_reward.get(
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
        except Exception as e:
            print(e)
            return

    def log(self, msg, level=1):
        if self.verbose >= level:
            print(f'(PyWitch) {msg}')
