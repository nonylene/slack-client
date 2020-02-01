import websocket
import urllib.parse
import urllib.request
import json
import traceback
import time
import click
from dataclasses import dataclass


@dataclass
class Config:
    token: str
    default_username: str
    emoji_watch_channel: str
    channel_watch_channel: str
    debug_channel: str


interrupted = False
channels = dict()
config: Config = None


def on_open(ws):
    message = "Connection opened!"
    print(message)
    # post slack
    post_text(config.debug_channel, message)


def on_close(ws, *close_args):
    message = "Connection closed!"
    print(message)
    # post slack error
    post_text(config.debug_channel, message)
    if not interrupted:
        # retry
        print("Reconnecting...")
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
        name = data["name"]
        emoji = f":{name}:"

        # If alias is added, we cannot know url.
        value = data['value']
        aliased = value.startswith('alias:')
        if aliased:
            message = f":raising_hand: Alias added: {emoji} (*{name}*, {value})"
            post_text(
                config.emoji_watch_channel, message,
                "emoji-bot", emoji,
            )

        else:
            message = f":raising_hand: Added: {emoji} (*{name}*)"

            block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
                "accessory": {
                    "type": "image",
                    "image_url": value,
                    "alt_text": emoji,
                }
            }
            data = {
                "text": message,
                "blocks": [block],
            }
            post_message(
                config.emoji_watch_channel, data,
                "emoji-bot", emoji
            )

    else:
        # Remove
        for name in data["names"]:
            message = f":wave: Removed: :{name}: (*{name}*)"
            post_text(
                config.emoji_watch_channel, message,
                "emoji-bot", ":upside_down_face:",
            )


def channel_watch(data):

    def channel_link(channel_id):
        return '<#{0}|{1}>'.format(channel_id, channels[channel_id])

    def post_channel_message(text):
        post_text(
            config.channel_watch_channel,
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
            ':hatching_chick: Created: {0}'.format(
                channel_link(channel_id)
            )
        )

    elif data['type'] == 'channel_deleted':
        channel_name = channels.pop(data['channel'])
        post_channel_message(
            ':see_no_evil: Deleted: #{0}'.format(channel_name)
        )

    elif data['type'] == 'channel_rename':
        channel_id = data['channel']['id']
        old_channel_name = channels[channel_id]
        new_channel_name = data['channel']['name']
        channels[channel_id] = new_channel_name
        post_channel_message(
            f':ocean: Renamed: {channel_link(channel_id)} (#{old_channel_name} :arrow_right: #{new_channel_name})'
        )

    elif data['type'] == 'channel_unarchive':
        post_channel_message(
            ':sushi: Unarchived: {0}'.format(channel_link(data['channel']))
        )


def connect():
    params = urllib.parse.urlencode({'token': config.token})
    try:
        # initial -> get channel list
        channels_api = "https://slack.com/api/channels.list?{0}".format(params)
        res = urllib.request.urlopen(channels_api)
        list_data = json.loads(res.read().decode())
        global channels
        channels = {c["id"]: c["name"] for c in list_data["channels"]}
    except Exception as e:
        traceback.print_exc()
        post_text(
            config.debug_channel,
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
        ws = websocket.WebSocketApp(
            websocket_url,
            on_message=on_message,
            on_error=on_error,
            on_open=on_open,
            on_close=on_close
        )

        ws.run_forever()

    except Exception as e:
        traceback.print_exc()
        post_text(
            config.debug_channel,
            "create websocket failed: {0}".format(e),
            ":upside_down_face:"
        )
        raise


def post_text(
        channel, text,
        username=None, icon_emoji=":upside_down_face:"
):
    if username is None:
        username = config.default_username
    post_message(channel, {"text": text}, username, icon_emoji)


def post_message(
        channel, data_dict,
        username=None, icon_emoji=":upside_down_face:"
):
    if username is None:
        username = config.default_username
    base = {
        "token": config.token,
        "channel": channel,
        "icon_emoji": icon_emoji,
        "username": username
    }
    merged = {**data_dict, **base}
    post_data = urllib.parse.urlencode(merged).encode()
    urllib.request.urlopen(
        "https://slack.com/api/chat.postMessage",
        data=post_data
    )


@click.command()
@click.option('--token', help='Slack token', type=str, required=True, show_envvar=True)
@click.option('--default-username', help='Default username', type=str, required=True, show_envvar=True)
@click.option('--emoji-watch-channel', help='emoji-watch channel', type=str, required=True,  show_envvar=True)
@click.option('--channel-watch-channel', help='channel-watch channel', type=str, required=True,  show_envvar=True)
@click.option('--debug-channel', help='Debug channel', type=str, required=True,  show_envvar=True)
def main(
    token, default_username, emoji_watch_channel, channel_watch_channel, debug_channel
):
    global config
    config = Config(
        token, default_username, emoji_watch_channel, channel_watch_channel, debug_channel
    )
    connect()


if __name__ == "__main__":
    main(auto_envvar_prefix='SLACK_CLIENT')
