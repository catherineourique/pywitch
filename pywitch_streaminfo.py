from websocket import create_connection
import time
import json
import threading
import requests
from .pywitch_functions import (
    validate_token,
    validate_callback,
    get_user_info,
    pywitch_log,
    json_eval,
)


class PyWitchStreamInfo:
    def __init__(
        self, channel, token, callback=None, users={}, interval=1, verbose=True
    ):
        self.channel = channel
        self.token = token
        self.callback = callback
        self.users = users
        self.interval = interval
        self.verbose = verbose

        validate_callback(callback)
        self.validation, self.helix_headers = validate_token(
            self.token, self.verbose
        )

        self.user_data = get_user_info(
            login=channel, helix_headers=self.helix_headers
        )
        self.users[self.user_data['user_id']] = self.user_data

        self.login = self.user_data['login']
        self.user_id = self.user_data['user_id']

        self.is_running = False
        self.data = None

    def event_listener(self):
        # This is not a 'real event', but we
        # can assume that to make it simplier
        try:
            while self.is_running:
                response = requests.get(
                    'https://api.twitch.tv/helix/streams',
                    headers=self.helix_headers,
                    params={'user_id': self.user_id},
                )
                if response.status_code == 200:
                    data = response.json()
                    data = data.get('data', [])
                    data = data and data[0] or {}
                    if self.data == data:
                        return
                    self.data = data
                    if self.callback:
                        self.callback(self.data)
                time.sleep(self.interval)
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

    def keep_alive(self):
        while self.is_running:
            self.event_listener()
