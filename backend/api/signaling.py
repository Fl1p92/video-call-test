import logging

import socketio

from backend import settings


log = logging.getLogger(__name__)
ROOM = 'room'
sio = socketio.AsyncServer(cors_allowed_origins=settings.ALLOWED_ORIGINS, ping_timeout=35)


@sio.event
async def connect(sid, environ):
    log.info(f'Connected: {sid}')
    await sio.emit('ready', room=ROOM, skip_sid=sid)
    sio.enter_room(sid, ROOM)


@sio.event
def disconnect(sid):
    sio.leave_room(sid, ROOM)
    log.info(f'Disconnected: {sid}')


@sio.event
async def data(sid, data):
    log.info(f'Message from {sid}: {data}')
    await sio.emit('data', data, room=ROOM, skip_sid=sid)
