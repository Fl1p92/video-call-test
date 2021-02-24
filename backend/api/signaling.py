import socketio

from backend import settings


ROOM = 'room'

sio = socketio.AsyncServer(cors_allowed_origins=settings.ALLOWED_ORIGINS, ping_timeout=35)


@sio.event
async def connect(sid, environ):
    # print('Connected', sid)  #ToDo Clear prints!
    await sio.emit('ready', room=ROOM, skip_sid=sid)
    sio.enter_room(sid, ROOM)


@sio.event
def disconnect(sid):
    sio.leave_room(sid, ROOM)
    # print('Disconnected', sid)  #ToDo Clear prints!


@sio.event
async def data(sid, data):
    # print('Message from {}: {}'.format(sid, data))  #ToDo Clear prints!
    await sio.emit('data', data, room=ROOM, skip_sid=sid)
