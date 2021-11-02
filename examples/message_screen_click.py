from pywitch import PyWitchTMI, PyWitchHeat, run_forever

token = 'YOUR_ACCESS_TOKEN'
channel = 'TARGET_CHANNEL'

shared_users = {}
clicking_users = {}


def tmi_callback(data):
    if data['message'] == 'start_track':
        clicking_users[data['user_id']] = True
        tmi.send(f"Now tracking {data['display_name']} click!")
        tmi.send(f"Please allow Heat Extension to read your user id")

    if data['message'] == 'stop_track' and data['user_id'] in clicking_users:
        clicking_users.pop(data['user_id'])
        tmi.send(f"Not tracking {data['display_name']} anymore!")


def heat_callback(data):
    if data['type'] == 'click' and data['user_id'] in clicking_users:
        user_data = shared_users.get(data['user_id'], {})
        display_name = user_data.get('display_name')
        if not display_name:
            return
        if data['x'] <= 0.5 and data['y'] <= 0.5:
            tmi.send(f'{display_name} clicked at the top left quadrant!')
        if data['x'] > 0.5 and data['y'] <= 0.5:
            tmi.send(f'{display_name} clicked at the top right quadrant!')
        if data['x'] <= 0.5 and data['y'] > 0.5:
            tmi.send(f'{display_name} clicked at the bottom left quadrant!')
        if data['x'] > 0.5 and data['y'] > 0.5:
            tmi.send(f'{display_name} clicked at the bottom right quadrant!')


tmi = PyWitchTMI(channel, token, tmi_callback, shared_users, verbose=False)
heat = PyWitchHeat(channel, token, heat_callback, shared_users, verbose=False)

tmi.start()
heat.start()

run_forever()
