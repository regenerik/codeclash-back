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
        _broadcast_to(request.sid, socketio)

    @socketio.on('disconnect')
    def handle_disconnect():
        user_id = request.sid
        parts = Participant.query.filter_by(user_id=user_id).all()
        room_ids = [p.room_id for p in parts]
        if parts:
            for p in parts:
                db.session.delete(p)
            db.session.commit()
            for room_id in room_ids:
                participants = [p.username for p in Room.query.get(room_id).participants]
                socketio.emit('update_participants', {'participants': participants}, room=room_id)
            _broadcast_all(socketio)
        print(f"<<< Cliente desconectado: {user_id}, eliminado de salas: {room_ids}")

    @socketio.on('list_rooms')
    def handle_list_rooms():
        _broadcast_to(request.sid, socketio)

    @socketio.on('create_room')
    def handle_create_room(data):
        user_id = request.sid
        username = data.get('username')
        room = Room(
            name=data.get('name', 'Sala sin nombre'),
            host_user_id=user_id,
            difficulty=data.get('difficulty'),
            password=data.get('password') or None
        )
        db.session.add(room)
        db.session.flush()
        db.session.add(Participant(room_id=room.id, user_id=user_id, username=username))
        db.session.commit()

        join_room(str(room.id))

        emit('room_created', {
            'id': room.id,
            'roomName': room.name,
            'difficulty': room.difficulty,
            'participants': [username]
        }, room=user_id)

        _broadcast_all(socketio)

    @socketio.on('join_room')
    def handle_join_room(data):
        user_id = request.sid
        room_id = data.get('room_id')
        username = data.get('username')
        pwd = data.get('password')
        room = Room.query.get(room_id)

        if not room:
            return emit('error', {'msg': 'Sala inexistente'}, room=user_id)
        if room.password and room.password != pwd:
            return emit('error', {'msg': 'Contraseña incorrecta'}, room=user_id)

        count = Participant.query.filter_by(room_id=room_id).count()
        if count >= 2:
            return emit('error', {'msg': 'Sala llena (2/2)'}, room=user_id)

        if not Participant.query.filter_by(room_id=room_id, user_id=user_id).first():
            db.session.add(Participant(room_id=room_id, user_id=user_id, username=username))
            db.session.commit()

        join_room(str(room.id))
        participants = [p.username for p in room.participants]
        emit('update_participants', {'participants': participants}, room=str(room_id))
        emit('server_message', {'msg': f"Usuario {username} se unió a la sala."}, room=str(room_id))

        _broadcast_all(socketio)
        return {'success': True}

    @socketio.on('leave_room')
    def handle_leave_room(data):
        user_id = request.sid
        room_id = data.get('room_id')

        part = Participant.query.filter_by(room_id=room_id, user_id=user_id).first()
        if part:
            db.session.delete(part)
            db.session.commit()

        room = Room.query.get(room_id)
        if room:
            participants = [p.username for p in Room.query.get(room_id).participants]
            socketio.emit('update_participants', {'participants': participants}, room=room_id)

        leave_room(room_id)
        _broadcast_all(socketio)

    @socketio.on('close_room')
    def handle_close_room(data):
        room_id = data.get('room_id')
        print(f"[codeclash] 🔥 handle_close_room: voy a hacer broadcast de room_deleted a la sala {room_id}")
        room = Room.query.get(room_id)
        if room:
            emit('room_deleted', {'room_id': str(room_id)}, room=str(room_id))
            db.session.delete(room)
            db.session.commit()
            _broadcast_all(socketio)

    @socketio.on('send_message')
    def handle_send_message(data):
        # Debug: imprimí en la consola del server
        room = str(data.get('room_id'))
        user = data.get('username')
        msg  = data.get('message')
        print(f"📝 [chat] recibí de {user} en sala {room}: «{msg}»")

        # Usá emit (importado) en lugar de socketio.emit, así toma la misma sala/namesp.
        emit(
            'new_message',
            {'username': user, 'message': msg},
            room=room
        )
        print(f"✅ [chat] mandé new_message a sala {room}")

def _broadcast_all(socketio):
    rooms = Room.query.filter_by(status='open').all()
    payload = [{
        'id': r.id,
        'name': r.name,
        'difficulty': r.difficulty,
        'hasPassword': bool(r.password),
        'count': Participant.query.filter_by(room_id=r.id).count(),
        'participants': [p.username for p in r.participants]
    } for r in rooms]
    emit('rooms_list', {'rooms': payload}, broadcast=True)

def _broadcast_to(sid, socketio):
    rooms = Room.query.filter_by(status='open').all()
    payload = [{
        'id': r.id,
        'name': r.name,
        'difficulty': r.difficulty,
        'hasPassword': bool(r.password),
        'count': Participant.query.filter_by(room_id=r.id).count(),
        'participants': [p.username for p in r.participants]
    } for r in rooms]
    socketio.emit('rooms_list', {'rooms': payload}, room=sid)
