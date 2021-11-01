from websocket import create_connection
import time
import json
import random
import threading
from .pywitch_functions import (
    validate_token,
    validate_callback,
    get_user_info,
    pywitch_log,
    json_eval,
)


def nonce(length):
    possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    text = ''.join(
        [possible[int(random.random() * len(possible))] for i in range(length)]
    )
    return text


class PyWitchRedemptions:
    def __init__(self, token, callback=None, users={}, verbose=True):
        self.token = token
        self.callback = callback
        self.users = users
        self.verbose = verbose

        validate_callback(callback)
        self.validation, self.helix_headers = validate_token(
            self.token, self.verbose
        )

        self.user_data = get_user_info(
            user_id=self.validation['user_id'],
            helix_headers=self.helix_headers,
        )
        self.users[self.user_data['user_id']] = self.user_data

        self.login = self.user_data['login']
        self.user_id = self.user_data['user_id']

        self.websocket = None
        self.is_running = False
        self.is_connected = False

    def connect(self):
        try:
            self.id_connected = False
            self.websocket = create_connection("wss://pubsub-edge.twitch.tv")
            self.websocket.send(json.dumps({'type': 'PING'}))
            data = {
                'type': "LISTEN",
                'nonce': nonce(15),
                'data': {
                    'topics': [f'channel-points-channel-v1.{self.user_id}'],
                    'auth_token': f'{self.token}',
                },
            }
            self.websocket.send(json.dumps(data))
            self.is_connected = True
        except Exception as e:
            print(e)
            return None

    def event_listener(self):
        try:
            while self.is_running:
                event = self.websocket.recv()
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
                self.data = {
                    'type': event_json.get('type'),
                    'data': event_data,
                    'login': event_user.get('login'),
                    'user_id': event_user.get('id'),
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

                if (
                    self.data['user_id']
                    and not self.data['user_id'] in self.users
                ):
                    self.users[self.data['user_id']] = {
                        'login': self.data['login'],
                        'user_id': self.data['user_id'],
                        'display_name': self.data['display_name'],
                    }

                if self.callback:
                    self.callback(self.data)
        except Exception as e:
            print(e)
            return None

    def start(self):
        if self.is_running:
            self.stop()
        self.thread = threading.Thread(target=self.keep_alive, args=())
        self.is_running = True
        self.thread.start()
        
    def stop(self):
        self.is_running = False
        self.is_connected = False
        self.websocket.close()
        self.websocket = None

    def keep_alive(self):
        while self.is_running:
            self.connect()
            self.event_listener()
