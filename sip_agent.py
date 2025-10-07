# import asyncio
# import logging
# from livekit import api, rtc
# from livekit.agents import WorkerOptions, JobContext
# import aiosip

# logging.basicConfig(level=logging.INFO)

# ASTERISK_SIP_USER = "2000"
# ASTERISK_SIP_PASS = "2000"
# ASTERISK_SIP_SERVER = "192.168.96.1"   # Asterisk server IP
# LOCAL_SIP_PORT = 5070                  # Port for our SIP client

# LIVEKIT_URL = "ws://localhost:7880"
# LIVEKIT_API_KEY = "APIntavBoHTqApw"
# LIVEKIT_API_SECRET = "pRkd16t4uYVUs9nSlNeMawSE1qmUzfV2ZkSrMT2aiFM"
# LIVEKIT_ROOM = "inbound-test"


# async def sip_agent():
#     # Create SIP application
#     app = aiosip.Application()
#     await app.connect(
#         local_addr=('0.0.0.0', LOCAL_SIP_PORT),
#         remote_addr=(ASTERISK_SIP_SERVER, 5060)
#     )

#     # Register SIP user 2000 with Asterisk
#     await app.register(
#         from_details=f'sip:{ASTERISK_SIP_USER}@{ASTERISK_SIP_SERVER}',
#         contact_uri=f'sip:{ASTERISK_SIP_USER}@{ASTERISK_SIP_SERVER}:{LOCAL_SIP_PORT}',
#         password=ASTERISK_SIP_PASS,
#         expires=3600
#     )

#     logging.info("✅ Registered as SIP user 2000 with Asterisk")

#     @app.on_invite
#     async def on_invite(request, message):
#         logging.info("📞 Incoming call from Asterisk")

#         # Accept SIP call
#         await request.reply(180)  # Ringing
#         await request.reply(200)  # OK

#         # Join LiveKit room
#         client = api.LiveKitAPI(
#             LIVEKIT_URL,
#             LIVEKIT_API_KEY,
#             LIVEKIT_API_SECRET
#         )
#         token = client.room.create_token(
#             room=LIVEKIT_ROOM,
#             identity="sip-2000",
#             name="SIP Gateway"
#         )

#         logging.info(f"🌐 Bridging call into LiveKit room: {LIVEKIT_ROOM}")

#         # TODO: Real RTP ↔ LiveKit media bridge
#         # For now, just simulate presence in room
#         lk_room = rtc.Room()
#         await lk_room.connect(LIVEKIT_URL, token)
#         logging.info("✅ Connected SIP call to LiveKit room")

#     await asyncio.Future()  # Run forever


# if __name__ == "__main__":
#     asyncio.run(sip_agent())
