from pywitch import PyWitchRedemptions, run_forever

token = 'YOUR_ACCESS_TOKEN'


def callback(data):
    print(data)


redemptions = PyWitchRedemptions(token, callback)

redemptions.start()

run_forever()
