# routes/socketio_bp.py
from flask import request
from flask_socketio import emit, join_room, leave_room
from database import db
from models import Room, Participant

def init_socketio(socketio):
    @socketio.on('connect')
    def handle_connect():
        print(f">>> Cliente conectado: {request.sid}")
        emit('server_message', {'msg': 'Bienvenido al CodeClash!'})
        _broadcast_to(request.sid, socketio)  # solo a este cliente

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"<<< Cliente desconectado: {request.sid}")

    @socketio.on('list_rooms')
    def handle_list_rooms():
        print(f"[server] list_rooms pedido por {request.sid}")
        _broadcast_to(request.sid, socketio)

    @socketio.on('create_room')
    def handle_create_room(data):
        user_id = request.sid
        print(f"[server] create_room de {user_id}: {data}")
        room = Room(
            name=data.get('name', 'Sala sin nombre'),
            host_user_id=user_id,
            difficulty=data.get('difficulty'),
            password=data.get('password') or None
        )
        db.session.add(room)
        db.session.flush()
        db.session.add(Participant(room_id=room.id, user_id=user_id))
        db.session.commit()

        emit('room_created', {
            'id': room.id,
            'name': room.name,
            'difficulty': room.difficulty,
            'hasPassword': bool(room.password)
        }, room=user_id)

        _broadcast_all(socketio)

    @socketio.on('join_room')
    def handle_join_room(data):
        user_id = request.sid
        room_id = data.get('room_id')
        pwd     = data.get('password')
        print(f"[server] join_room {room_id} pedido por {user_id} (pwd={pwd})")
        room = Room.query.get(room_id)
        if not room:
            return emit('error', {'msg': 'Sala inexistente'}, room=user_id)
        if room.password and room.password != pwd:
            return emit('error', {'msg': 'Contraseña incorrecta'}, room=user_id)

        count = Participant.query.filter_by(room_id=room_id).count()
        print(f"[server] actualmente hay {count} participantes en sala {room_id}")
        if count >= 2:
            return emit('error', {'msg': 'La sala ya está llena (2/2)'}, room=user_id)

        if not Participant.query.filter_by(room_id=room_id, user_id=user_id).first():
            db.session.add(Participant(room_id=room_id, user_id=user_id))
            db.session.commit()

        join_room(room_id)
        emit('joined_room', {'room_id': room_id}, room=user_id)
        emit('server_message', {'msg': f"Usuario {user_id} se unió a sala {room_id}"}, room=room_id)

        _broadcast_all(socketio)

    @socketio.on('leave_room')
    def handle_leave_room(data):
        user_id = request.sid
        room_id = data.get('room_id')
        print(f"[server] leave_room {room_id} pedido por {user_id}")
        part = Participant.query.filter_by(room_id=room_id, user_id=user_id).first()
        if part:
            db.session.delete(part)
            db.session.commit()
        leave_room(room_id)
        _broadcast_all(socketio)

    @socketio.on('delete_room')
    def handle_delete_room(data):
        room_id = data.get('room_id')
        print(f"[server] delete_room {room_id}")
        room = Room.query.get(room_id)
        if room:
            db.session.delete(room)
            db.session.commit()
        _broadcast_all(socketio)


def _broadcast_all(socketio):
    """Envía el rooms_list a todos los sockets conectados."""
    rooms = Room.query.filter_by(status='open').all()
    payload = [{
        'id': r.id,
        'name': r.name,
        'difficulty': r.difficulty,
        'hasPassword': bool(r.password),
        'count': Participant.query.filter_by(room_id=r.id).count()
    } for r in rooms]
    print("[server] broadcast rooms_list:", payload)
    emit('rooms_list', {'rooms': payload}, broadcast=True)


def _broadcast_to(sid, socketio):
    """Envía el rooms_list solo al socket `sid`."""
    rooms = Room.query.filter_by(status='open').all()
    payload = [{
        'id': r.id,
        'name': r.name,
        'difficulty': r.difficulty,
        'hasPassword': bool(r.password),
        'count': Participant.query.filter_by(room_id=r.id).count()
    } for r in rooms]
    socketio.emit('rooms_list', {'rooms': payload}, room=sid)
