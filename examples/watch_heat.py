from pywitch import PyWitchHeat, run_forever

token = 'YOUR_ACCESS_TOKEN'
channel = 'TARGET_CHANNEL'


def callback(data):
    print(data)


heat = PyWitchHeat(channel, token, callback)

heat.start()

run_forever()
