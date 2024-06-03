import asyncio
import json
import logging
import random
import string
import sys
import time
import uuid
from urllib.parse import urlparse

import aiortc
import requests
from OpenSSL import crypto
from OpenSSL.crypto import FILETYPE_PEM
from aiortc import RTCSessionDescription, RTCIceCandidate, MediaStreamTrack, VideoStreamTrack, RTCConfiguration, \
    RTCIceServer, RTCPeerConnection, RTCDtlsTransport, RTCCertificate
from aiortc.contrib.media import MediaPlayer, MediaBlackhole, MediaRecorder
from aiortc.contrib.signaling import BYE
from aiortc.contrib.signaling import CopyAndPasteSignaling, object_from_string, \
    object_to_string

HOST = "https://alpha.webinar.ru/api"
event_session_id = "1864387567"
creator_id = ""


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


async def pc_method(session, peer: RTCPeerConnection, params):
    # channel = peer.createDataChannel("screen", ordered=True)
    player = MediaPlayer("media.mp4", decode=False, options={
        'video_size': '640x480',
        'vcodec': 'libx264'
    })

    sender = peer.addTrack(player.video)
    recorder = MediaRecorder("recoeded.mp4")

    @pc.on("track")
    def on_track(track):
        print("Receiving %s" % track.kind)
        recorder.addTrack(track)

    # async def send_pings():
    #     while True:
    #         channel_send(channel, "ping %d" % current_stamp())
    #         await asyncio.sleep(1)

    # @peer.on("open")
    # def on_open():
    #     asyncio.ensure_future(send_pings())

    @peer.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        print(f"ICE connection state is {peer.iceConnectionState}")

    @peer.on("message")
    def on_message(msg):
        print(f"MESSAGE: {msg}")

    offer = await peer.createOffer()
    await peer.setLocalDescription(offer)
    body = peer.localDescription.sdp
    print(body)

    with session.post(rtc_host + f"/rtc/room/{event_session_id}/stream/{private_key}",
                      params=params, data=body) as res_guest:
        print(res_guest.status_code)

    message = {
        "sdp": res_guest.content.decode('UTF-8'),
        "type": "answer"
    }

    obj = RTCSessionDescription(**message)

    # obj = await signaling.receive()
    # while True:
    await peer.setRemoteDescription(obj)
    await recorder.start()
    # print(peer.event_names())

    body = {
        "status": "PUBLISH",
        "hasVideo": "true",
        "hasAudio": "false"
    }
    print(screen_id)
    with session.put(HOST + f"/screensharings/{screen_id}", data=body) as res_guest:
        print(res_guest.status_code)
        # print(res_guest.content)

    while True:
        # print(f"video state: {player.video.readyState}")
        # print(f"signaling state: {peer.signalingState}")
        # print(f"connection state: {peer.connectionState}")
        # print(f"ice connection state: {peer.iceConnectionState}")
        # print(f"ice gathering state: {peer.iceGatheringState}")
        # stats = await sender.getStats()
        stats = await peer.getStats()
        print(f"STATS: {stats}")
        print("=================================================")
        # if player.video.readyState == "ended" or peer.connectionState == 'failed':
        #     break
        # track_sender.send()
        await asyncio.sleep(3)


def connect_to_webinar(session):
    # payload_total_16 = {
    #     "email": "user_load_ddeivfuxos@qa-mail.webinar.ru",
    #     "password": "12345678",
    #     "rememberMe": True}
    guest_payload = {"nickname": "some name"}
    session.post(HOST + f"/eventsessions/{event_session_id}/guestlogin", data=guest_payload)

    session.get(HOST + "/login")
    # connecting admin
    session.post(HOST + f"/eventsessions/{event_session_id}/connections")

    # get wss configuration for socket
    session.get(HOST + f"/eventsession/{event_session_id}/configuration")

    session.get(HOST + f"/eventsessions/{event_session_id}/myscreensharings")

    res_guest = session.post(HOST + f"/eventsessions/{event_session_id}/screensharings")

    return res_guest


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    ses = requests.session()
    res_guest = connect_to_webinar(ses)

    # get webRTC url and params
    rtc_url = urlparse(res_guest.json()["rtcUrl"])
    rtmp_url = res_guest.json()["rtmpUrl"]
    rtc_host = "https://" + rtc_url.netloc
    private_key = res_guest.json()["privateKey"]
    screen_id = res_guest.json()["id"]
    username = res_guest.json()["user"]["nickname"]
    creator_id = res_guest.json()["user"]["id"]
    uid = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', k=16))

    params = {
        "userId": creator_id,
        "userName": username,
        "transport": "any",
        "sessionId": f"{creator_id}_{uid}",
        "disableBridge": "true",
        "disableRecording": "false",
    }
    pc = RTCPeerConnection()

    coro = pc_method(ses, pc, params)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(coro)
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(pc.close())
