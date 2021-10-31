from websocket import create_connection
import time
import json
import random
import requests
import threading
import time
from pywitch_tmi import TMI
from pywitch_redemptions import Redemptions


### Auxiliary functions ######################################################


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
            #'rewards': [self.connect_rewards, self.event_rewards],
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

    ##############################################################################

    ### Start functions ##########################################################

    def start_tmi(self, channel, callback=None):
        self.instances['tmi'] = TMI(self, channel, callback)
        self.instances['tmi'].start_thread()
        return self.instances['tmi']

    def start_redemptions(self, channel, callback=None):
        self.instances['redemptions'] = Redemptions(self, channel, callback)
        self.instances['redemptions'].start_thread()
        return self.instances['redemptions']

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


##############################################################################
