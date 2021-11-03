from websocket import create_connection
import time
import json
import threading
from .pywitch_functions import (
    validate_token,
    validate_callback,
    get_user_info,
    pywitch_log,
    json_eval,
)


class PyWitchHeat:
    def __init__(self, channel, token, callback=None, users={}, verbose=True):
        self.channel = channel
        self.token = token
        self.callback = callback
        self.users = users
        self.verbose = verbose

        validate_callback(callback)
        self.validation, self.helix_headers = validate_token(
            self.token, self.verbose
        )

        self.user_data = get_user_info(
            login=channel, helix_headers=self.helix_headers
        )
        self.users[self.user_data['user_id']] = self.user_data

        self.channel_data = get_user_info(
            login=self.channel,
            helix_headers=self.helix_headers,
        )
        if not self.channel_data['user_id']:
            raise Exception(
                f"{self.channel} is not a valid channel for Heat Extension"
            )

        self.users[self.channel_data['user_id']] = self.channel_data

        self.login = self.user_data['login']
        self.user_id = self.user_data['user_id']

        self.thread = None
        self.websocket = None
        self.is_running = False
        self.is_connected = False

    def connect(self):
        try:
            self.id_connected = False
            self.websocket = create_connection(
                f"wss://heat-api.j38.net/channel/{self.user_id}"
            )
            self.is_connected = True
        except Exception as e:
            if e.status_code == 404:
                raise Exception(
                    f"{self.channel} is not a valid channel"
                    " for Heat Extension"
                )
            print(e)
            return None

    def event_listener(self):
        try:
            while self.is_running:
                event = self.websocket.recv()
                event_data = json_eval(event)
                event_user = str(event_data.get('id', ''))
                if not event_user:
                    continue

                self.data = {
                    'type': event_data.get('type'),
                    'message': event_data.get('message'),
                    'type': event_data.get('type'),
                    'user_id': event_user,
                    'event_raw': event,
                    'event_time': time.time(),
                }

                try:
                    x = float(event_data.get('x', 0))
                    y = float(event_data.get('y', 0))
                    self.data['x'] = x
                    self.data['y'] = y
                except:
                    continue

                if event_user in self.users:
                    self.data.update(self.users[event_user])
                elif event_user.isdigit():
                    self.users[event_user] = {
                        'user_id': event_user,
                        'display_name': '',
                        'login': '',
                    }
                    request = threading.Thread(
                        target=self.request_user_info, args=(event_user,)
                    )
                    request.start()

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
        if self.thread:
            self.thread.join()
            self.thread = None

    def keep_alive(self):
        while self.is_running:
            self.connect()
            self.event_listener()

    def request_user_info(self, user_id):
        user_data = get_user_info(
            user_id=user_id, helix_headers=self.helix_headers
        )
        if user_data:
            self.users[user_data['user_id']] = user_data
