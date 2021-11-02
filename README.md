# PyWitch
![pywitch_logo](logo/pywitch_logo.png)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

PyWitch is a library that integrate Twitch with Python using requests and
websockets.

The functionalities included are: 

⋅⋅* Token Validation;

⋅⋅* StreamInfo (real time stream information);

⋅⋅* TMI (twitch Messaging Interface);

⋅⋅* Redemptions (chat redemptions and rewards);

⋅⋅* Heat (heat extension).

## Token Generation ##

To generate token, you need to authenticate PyWitch application in the
following URL:

https://id.twitch.tv/oauth2/authorize?response_type=token&client_id=l2o6fudb8tq6394phgudstdzlouo9n&redirect_uri=https://localhost&scope=channel:manage:redemptions%20channel:read:redemptions%20user:read:email%20chat:edit%20chat:read

NOTE: This URL will provide the following scopes to PyWitch application:

[channel:manage:redemptions, channel:read:redemptions, user:read:email,
chat:edit, chat:read]

It will ask for you to login in your Twitch Account to authorize. After
authorizing it, it will redirect to an (usually) broken page. The only thing
you need from the page is its URL. Copy that URL, it should look like this:

https://localhost/#access_token=YOUR_ACCESS_TOKEN&scope=channel%3Amanage%3Aredemptions+channel%3Aread%3Aredemptions+user%3Aread%3Aemail+chat%3Aedit+chat%3Aread&token_type=bearer

Your token is what is filling YOUR_ACCESS_TOKEN from the URL. 

Alternatively, you can create a Twitch Application in the
following URL:

https://dev.twitch.tv

To do so, first login with your Twitch Account, click "Your Console", then 
"Applications" and "Register Your Application".

Give it a pretty name and set OAuth Redirect URLs as "https://localhost", and
set Category to any of the given options.

After that, your application will receive an "Client ID", keep that in hands.

Now you need to access the following URL, replacing 'l2o6fudb8tq6394phgudstdzlouo9n'
with your application client_id:
