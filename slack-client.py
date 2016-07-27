import websocket
import urllib.parse
import urllib.request
import json
import traceback

import config

interrupted = False

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

# client features below here
def emoji_watch(data):
    # https://api.slack.com/events/emoji_changed
    if not "emoji_changed" == data["type"]:
        return

    subtype = data["subtype"]
    if "add" == subtype:
        icon_emoji = ":{0}:".format(data["name"])
        prefix_emoji = ":raising_hand:"
        emojis = [data["name"]]
    else:
        icon_emoji = ":upside_down_face:"
        prefix_emoji = ":wave:"
        emojis = data["names"]

    for emoji in emojis:
        emoji_str = ":{0}:".format(emoji)
        message = "{0} {1} {2}!".format(prefix_emoji, emoji_str, data["subtype"])
        post_message(config.EMOJI_WATCH_CHANNEL, message, username = "Emoji Watcher", icon_emoji = icon_emoji)

def connect():
    try:
        params = urllib.parse.urlencode({'token': config.TOKEN})
        start_api = "https://slack.com/api/rtm.start?{0}".format(params)
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
        post_message(config.DEBUG_CHANNEL, str(e), ":upside_down_face:")

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

