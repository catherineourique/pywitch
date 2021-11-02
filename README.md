# PyWitch
![pywitch_logo](logo/pywitch_logo.png)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)


PyWitch is a library that integrate Twitch with Python using requests and
websockets.

The functionalities included are: 

* Token Validation;

* StreamInfo (real time stream information);

* TMI (twitch Messaging Interface);

* Redemptions (chat redemptions and rewards);

* Heat (heat extension).

## Requirements ##

Tested in Python 3.7

Libraries:
```
requests>=2.26.0
websocket-client>=1.2.1
```

## Token Validation ##

To validate your token, you can use the following function:

```
from pywitch import validate_token

token = 'YOUR_TOKEN'
validation, helix_headers = validate_token(token)
```

Where `validation` is a dictionary with token validation information and
`helix_headers` contains the headers necessary for requests into Twitch API.

## PyWitchStreamInfo ##

PyWitchStreamInfo is a class that request stream information from Twitch API
and everytime the response changes, a predefined function is called (callback).

Use:
```
from pywitch import PyWitchStreamInfo, run_forever

def callback(data):
    print(data)

token = 'YOUR_TOKEN'
channel = 'TARGET_CHANNEL'
users = {} # Shared user list minimzes the number of requests

streaminfo = PyWitchStreamInfo(
    channel = channel,
    token = token,
    callback = callback, # Optional
    users = users,       # Optional, but strongly recomended
    interval = 1,        # Optional
    verbose = True,      # Optional
)
streaminfo.start()
run_forever()
```

It automatically validate the provided token. 

The `data` parameter in the callback function is a dictionary with the
following keys:
```
['id', 'user_id', 'user_login', 'user_name', 'game_id', 'game_name',
 'type', 'title', 'viewer_count', 'started_at', 'language', 'thumbnail_url',
 'tag_ids', 'is_mature', 'event_time']
```

## PyWitchTMI ##

PyWitchTMI is a class that manages the connection with TMI using websockets.
With this class, messages sent to Twitch chat calls a predefined funcion. It
can also send messages to chat using the account associated account.

Use:

```
from pywitch import PyWitchTMI, run_forever

def callback(data):
    print(data)

token = 'YOUR_TOKEN'
channel = 'TARGET_CHANNEL'
users = {} # Shared user list minimzes the number of requests

tmi = PyWitchTMI(
    channel = channel,
    token = token,
    callback = callback, # Optional
    users = users,       # Optional, but strongly recomended
    verbose = True,      # Optional
)
tmi.start()
tmi.send('PyWitch send a message!')
run_forever()
```

Note: The channel don't need to be the same as the one that provided the
token.

It automatically validate the provided token. 

The `data` parameter in the callback function is a dictionary with the
following keys:
```
['display_name', 'event_time', 'user_id', 'login', 'message', 'event_raw']
```

Event time is given by `time.time()`.

## PyWitchRedemptions ##

PyWitchRedemptions is a class that reads the user chat redemptions.
With this class, users chat redemptions calls a predefined funcion.

Use:

```
from pywitch import PyWitchRedemptions, run_forever

def callback(data):
    print(data)

token = 'YOUR_TOKEN'
users = {} # Shared user list minimzes the number of requests

redemptions = PyWitchRedemptions(
    token = token,
    callback = callback, # Optional
    users = users,       # Optional, but strongly recomended
    verbose = True,      # Optional
)
redemptions.start()
run_forever()
```

Note: Due to Twitch limitations, the provided token need to be generated with
the broadcaster user.

It automatically validate the provided token. 

The `data` parameter in the callback function is a dictionary with the
following keys:
```
['type', 'data', 'login', 'user_id', 'display_name', 'title', 'prompt',
 'cost', 'user_input', 'cooldown', 'message', 'event_dict', 'event_time',
 'event_raw']
```

Event time is given by `time.time()`.

## PyWitchHeat ##

PyWitchHeat is a class that reads from Heat Extension websocket.

[Heat Extension allows you to capture the users click on screen, you can find more information about it in this URL: https://heat.j38.net/about/](https://heat.j38.net/about/)

Use:

```
from pywitch import PyWitchHeat, run_forever

def callback(data):
    print(data)

token = 'YOUR_TOKEN'
chanel = 'TARGET_CHANNEL
users = {} # Shared user list minimzes the number of requests

heat = PyWitchHeat(
    token = token,
    callback = callback, # Optional
    users = users,       # Optional, but strongly recomended
    verbose = True,      # Optional
)
heat.start()
run_forever()
```

Since Heat only returns user_id, every new user that click on screen execute
a request on Twitch API to recover its user display_name and login.
Using shared user lists minimizes the number of requests drastically.

For users that don't authorize the Heat Extension to read the user id, it will
only return the opaque user id.

It automatically validate the provided token. 

The `data` parameter in the callback function is a dictionary with the
following keys:
```
['type', 'message', 'user_id', 'event_raw', 'event_time', 'x', 'y', 'login',
 'display_name']
```

Event time is given by `time.time()`.

## Token Generation ##

To generate token, you need to authenticate PyWitch application in the
following URL:

```
https://id.twitch.tv/oauth2/authorize?response_type=token&client_id=l2o6fudb8tq6394phgudstdzlouo9n&redirect_uri=https://localhost&scope=channel:manage:redemptions%20channel:read:redemptions%20user:read:email%20chat:edit%20chat:read
```

NOTE: This URL will provide the following scopes to PyWitch application:

[channel:manage:redemptions, channel:read:redemptions, user:read:email,
chat:edit, chat:read]

It will ask for you to login in your Twitch Account to authorize. After
authorizing it, it will redirect to an (usually) broken page. The only thing
you need from the page is its URL. Copy that URL, it should look like this:

```
https://localhost/#access_token=YOUR_ACCESS_TOKEN&scope=channel%3Amanage%3Aredemptions+channel%3Aread%3Aredemptions+user%3Aread%3Aemail+chat%3Aedit+chat%3Aread&token_type=bearer
```

Your token is what is filling YOUR_ACCESS_TOKEN from the URL. 

Alternatively, you can create a Twitch Application in the
following URL:

[https://dev.twitch.tv](https://dev.twitch.tv)

To do so, first login with your Twitch Account, click "Your Console", then 
"Applications" and "Register Your Application".

Give it a pretty name and set OAuth Redirect URLs as "https://localhost", and
set Category to any of the given options.

After that, your application will receive an "Client ID", keep that in hands.

Now you need to access the following URL, replacing `l2o6fudb8tq6394phgudstdzlouo9n`
with your application client_id:
