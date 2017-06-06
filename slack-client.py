import websocket
import urllib.parse
import urllib.request
import json
import traceback
import time

import config

interrupted = False
channels = dict()

def on_open(ws):
    message = "connection opened!"
    print(message)
    # post slack
    post_message(config.DEBUG_CHANNEL, message)

def on_close(ws, *close_args):
    message = "connection closed!"
    print(message)
    # post slack error
    post_message(config.DEBUG_CHANNEL, message)
    if not interrupted:
        # retry
        print("reconnecting...")
        time.sleep(2)
        connect()

def on_error(ws, error):
    traceback.print_exc()
    # KeyboardInterrupt arrive here (0.37)
    # SystemError not arrive here (0.37~)
    if isinstance(error, SystemError) or isinstance(error, KeyboardInterrupt):
        global interrupted
        interrupted = True

def on_message(ws, message):
    message_data = json.loads(message)
    emoji_watch(message_data)
    channel_watch(message_data)

# client features below here
def emoji_watch(data):
    # https://api.slack.com/events/emoji_changed
    if not "emoji_changed" == data["type"]:
        return

    subtype = data["subtype"]
    if "add" == subtype:
        icon_emoji = ":{0}:".format(data["name"])
        prefix_emoji = ":raising_hand:"
        text = "Added"
        emojis = [data["name"]]
    else:
        icon_emoji = ":upside_down_face:"
        prefix_emoji = ":wave:"
        text = "Removed"
        emojis = data["names"]

    for emoji in emojis:
        message = "{0} {1}: :{2}: ({2})".format(prefix_emoji, text, emoji)
        post_message(config.EMOJI_WATCH_CHANNEL, message, username = "Emoji Watcher", icon_emoji = icon_emoji)

def channel_watch(data):

    def channel_link(channel_id):
        return '<#{0}|{1}>'.format(channel_id, channels[channel_id])

    def post_channel_message(text):
        post_message(
                config.CHANNEL_WATCH_CHANNEL,
                text,
                'channel-bot',
                ':tokyo_tower:'
                )

    # https://api.slack.com/events/channel_archive
    # https://api.slack.com/events/channel_created
    # https://api.slack.com/events/channel_deleted
    # https://api.slack.com/events/channel_rename
    # https://api.slack.com/events/channel_unarchive
    if data['type'] == 'channel_archive':
        post_channel_message(
                ':ghost: Archived: {0}'.format(channel_link(data['channel']))
                )

    elif data['type'] == 'channel_created':
        channel_id = data['channel']['id']
        channels[channel_id] = data['channel']['name']
        post_channel_message(
                ':hatching_chick: Created: {0}'.format(channel_link(channel_id))
                )

    elif data['type'] == 'channel_deleted':
        channel_name = channels.pop(data['channel'])
        post_channel_message(
                ':see_no_evil: Deleted: #{0}'.format(channel_name)
                )

    elif data['type'] == 'channel_rename':
        channel_id = data['channel']['id']
        old_channel_name = channels[channel_id]
        channels[channel_id] = data['channel']['name']
        post_channel_message(
                ':fog: Renamed: #{0} :arrow_right: {1}'.format(
                    old_channel_name,
                    channel_link(channel_id)
                    )
                )

    elif data['type'] == 'channel_unarchive':
        post_channel_message(
                ':sushi: Unarchived: {0}'.format(channel_link(data['channel']))
                )

def connect():
    params = urllib.parse.urlencode({'token': config.TOKEN})
    try:
        # initial -> get channel list
        channels_api = "https://slack.com/api/channels.list?{0}".format(params)
        res = urllib.request.urlopen(channels_api)
        list_data = json.loads(res.read().decode())
        global channels
        channels = {c["id"]: c["name"] for c in list_data["channels"]}
    except Exception as e:
        traceback.print_exc()
        post_message(config.DEBUG_CHANNEL,
                "get channel list failed: {0}".format(e),
                ":upside_down_face:"
                )
        raise

    try:
        start_api = "https://slack.com/api/rtm.connect?{0}".format(params)
        res = urllib.request.urlopen(start_api)
        start_data = json.loads(res.read().decode())
        websocket_url = start_data["url"]
        # websocket.enableTrace(True)
        ws = websocket.WebSocketApp(websocket_url,
                on_message = on_message,
                on_error = on_error,
                on_open = on_open,
                on_close = on_close
                )

        ws.run_forever()

    except Exception as e:
        traceback.print_exc()
        post_message(config.DEBUG_CHANNEL,
                "create websocket failed: {0}".format(e),
                ":upside_down_face:"
                )
        raise

def post_message(channel, text, username=config.DEFAULT_USERNAME, icon_emoji=":upside_down_face:"):
    data = {
            "token": config.TOKEN,
            "channel": channel,
            "text": text,
            "icon_emoji": icon_emoji,
            "username": username
            }
    post_data = urllib.parse.urlencode(data).encode()
    urllib.request.urlopen("https://slack.com/api/chat.postMessage", data = post_data)

connect()

