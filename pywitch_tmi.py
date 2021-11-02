from websocket import create_connection
import time
import threading

from .pywitch_functions import (
    validate_token,
    validate_callback,
    get_user_info,
    pywitch_log,
)


def get_display_name(string):
    return string.split(';display-name=')[-1].split(';')[0].strip()


def get_user_id(string):
    return string.split(';user-id=')[-1].split(';')[0].strip()


def get_login(string):
    return string.split('.tmi.twitch.tv')[0].split('@')[-1]


def get_privmsg(string):
    try:
        ipos = string.find('PRIVMSG')
        ipos = string.find(':', ipos) + 1
        fpos = string.find('\r\n', ipos)
        return string[ipos:fpos]
    except:
        return ''


class PyWitchTMI:
    def __init__(
        self, channel, token=None, callback=None, users={}, verbose=True
    ):
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
            user_id=self.validation['user_id'],
            helix_headers=self.helix_headers,
        )
        self.users[self.user_data['user_id']] = self.user_data

        self.channel_data = get_user_info(
            login=self.channel,
            helix_headers=self.helix_headers,
        )
        if not self.channel_data['user_id']:
            raise Exception(f"{self.channel} is not a valid channel for TMI")

        self.users[self.channel_data['user_id']] = self.channel_data

        self.login = self.user_data['login']

        self.websocket = None
        self.is_running = False
        self.is_connected = False

    def connect(self):
        try:
            self.is_connected = False
            self.websocket = create_connection(
                "wss://irc-ws.chat.twitch.tv:443"
            )
            cap = 'twitch.tv/tags twitch.tv/commands twitch.tv/membership'
            self.websocket.send(f'CAP REQ : {cap}')
            self.websocket.send(f'PASS oauth:{self.token}')
            self.websocket.send(f'NICK {self.login}')
            self.websocket.send(f'JOIN #{self.channel}')
            self.is_connected = True
        except Exception as e:
            print(e)
            return None

    def event_listener(self):
        try:
            while self.is_running:
                event = self.websocket.recv()
                if not 'PRIVMSG' in event:
                    continue
                event_time = time.time()
                display_name = get_display_name(event)
                user_id = get_user_id(event)
                login = get_login(event)
                if not user_id in self.users:
                    self.users[user_id] = {
                        'user_id': user_id,
                        'display_name': display_name,
                        'login': login,
                    }
                message = get_privmsg(event)
                self.data = {
                    'display_name': display_name,
                    'event_time': event_time,
                    'user_id': user_id,
                    'login': login,
                    'message': message,
                    'event_raw': event,
                }
                if self.callback:
                    self.callback(self.data)
        except Exception as e:
            print(e)
            return

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

    def send(self, message):
        if not self.is_running:
            pywitch_log(
                'TMI not connected! Please first execute "start" function.',
                self.verbose,
            )
            return
        while not (hasattr(self, 'websocket') and self.is_connected):
            time.sleep(0.1)
        self.websocket.send(f'PRIVMSG #{self.channel} :{message}')
