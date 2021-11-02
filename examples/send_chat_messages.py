from pywitch import PyWitchTMI

token = 'YOUR_ACCESS_TOKEN'
channel = 'TARGET_CHANNEL'

tmi = PyWitchTMI(channel, token)

tmi.start()

tmi.send('Hey, PyWitch is sending messages!')
tmi.send('Enjoy!')

tmi.stop()
