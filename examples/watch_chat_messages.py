from pywitch import PyWitchTMI, run_forever

token = 'YOUR_ACCESS_TOKEN'
channel = 'TARGET_CHANNEL'


def callback(data):
    print(data)


tmi = PyWitchTMI(channel, token, callback)

tmi.start()

run_forever()
