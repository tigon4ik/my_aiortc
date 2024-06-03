import asyncio
import time

import aiortc
import requests
from aiortc import RTCSessionDescription, RTCPeerConnection
from aiortc.contrib.media import MediaBlackhole, MediaPlayer
from aiortc.contrib.signaling import object_from_string

HOST = "https://alpha.webinar.ru/api"
event_session_id = "189205327"
creator_id = ""
time_start = None


def channel_log(channel, t, message):
    print("channel(%s) %s %s" % (channel.label, t, message))


def channel_send(channel, message):
    channel_log(channel, ">", message)
    channel.send(message)


def current_stamp():
    global time_start

    if time_start is None:
        time_start = time.time()
        return 0
    else:
        return int((time.time() - time_start) * 1000000)


async def pc_method(session, peer: RTCPeerConnection):
    # channel = peer.createDataChannel("chat")

    # channel_log(channel, "-", "created by local party")
    player = MediaPlayer("media.mp4", options={
        'video_size': '640x480',
        'vcodec': 'libx264'
    })
    recorder = MediaBlackhole()
    peer.addTrack(player.video)

    # async def send_pings():
    #     while True:
    #         channel_send(channel, "ping %d" % current_stamp())
    #         await asyncio.sleep(1)

    # @peer.on("iceconnectionstatechange")
    # async def on_iceconnectionstatechange():
    #     print(f"ICE connection state is {peer.iceConnectionState}")

    @pc.on("track")
    def on_track(track):
        print("Receiving %s" % track.kind)
        recorder.addTrack(track)

    # @channel.on("open")
    # def on_open():
    #     asyncio.ensure_future(send_pings())
    #
    # @channel.on("message")
    # def on_message(message):
    #     channel_log(channel, "<", message)

        # if isinstance(message, str) and message.startswith("pong"):
        #     elapsed_ms = (current_stamp() - int(message[5:])) / 1000
        #     print(" RTT %.2f ms" % elapsed_ms)

    await peer.setLocalDescription(await peer.createOffer())

    while peer.localDescription is None:
        print("waiting local description")
        await asyncio.sleep(1)

    body = {
        "sdp": peer.localDescription.sdp,
        "type": peer.localDescription.type,
        "video_transform": 'none'
    }

    with session.post("http://localhost:8080/offer", json=body) as res_guest:
        print(res_guest.status_code)

    obj = RTCSessionDescription(**res_guest.json())
    # obj = object_from_string(res_guest.content.decode("utf-8"))

    await peer.setRemoteDescription(obj)

    # print(peer.remoteDescription.sdp)
    while peer.remoteDescription is None:
        print("waiting remote description")
        await asyncio.sleep(1)

    await recorder.start()

    while True:
        # print(f"video state: {webcam.video.readyState}")
        print(f"connection state: {peer.connectionState}")
        print(f"ice connection state: {peer.iceConnectionState}")
        print(f"ice gathering state: {peer.iceGatheringState}")
        print("=================================================")
        # if webcam.video.readyState == "ended":
        #     break
        # track_sender.send()
        await asyncio.sleep(3)


if __name__ == "__main__":
    ses = requests.session()

    pc = RTCPeerConnection()

    coro = pc_method(ses, pc)
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(coro)
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(pc.close())
