from pywitch import PyWitchStreamInfo, run_forever

token = 'YOUR_ACCESS_TOKEN'
channel = 'TARGET_CHANNEL'


def callback(data):
    print(data)


streaminfo = PyWitchStreamInfo(channel, token, callback)

streaminfo.start()

run_forever()
