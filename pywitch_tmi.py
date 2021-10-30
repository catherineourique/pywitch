from websocket import create_connection
import time
import json
import random
import requests
import threading
import time


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


class TMI:
    def __init__(self, pywitch, channel, callback=None):
        self.pywitch = pywitch
        self.token = pywitch.token
        self.login = pywitch.user['login']
        self.channel = channel
        self.callback = callback

        self.validate_callback()

        self.kind = 'tmi'
        self.websocket = None
        self.is_running = False
        self.is_connected = False

    def validate_callback(self):
        if not callable(self.callback) and self.callback != None:
            raise Exception("Provided callback is not callable! Terminating.")

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
                if not user_id in self.pywitch.users:
                    self.pywitch.users[user_id] = {
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

    def start_thread(self):
        self.thread = threading.Thread(target=self.keep_alive, args=())
        self.is_running = True
        self.thread.start()

    def keep_alive(self):
        while self.is_running:
            self.connect()
            self.event_listener()

    def send(self, message):
        self.websocket.send('PRIVMSG #{self.channel} :{message}')
