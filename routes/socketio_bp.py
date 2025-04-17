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
        user_id  = request.sid
        username = data.get('username')
        room = Room(
            name=data.get('name', 'Sala sin nombre'),
            host_user_id=user_id,
            difficulty=data.get('difficulty'),
            password=data.get('password') or None
        )
        db.session.add(room)
        db.session.flush()   # para tener room.id
        # 1) guardo al host como participante
        db.session.add(Participant(room_id=room.id, user_id=user_id, username=username))
        db.session.commit()

        # 2) meto al host en el canal socketio "room"
        join_room(room.id)

        # 3) aviso al host por "room_created"
        emit('room_created', {
            'id': room.id,
            'roomName': room.name,
            'difficulty': room.difficulty,
            'participants': [username]
        }, room=user_id)

        # 4) refresco el lobby en todas las pestañas
        _broadcast_all(socketio)


    @socketio.on('join_room')
    def handle_join_room(data):
        user_id  = request.sid
        room_id  = data.get('room_id')
        username = data.get('username')
        pwd      = data.get('password')
        room = Room.query.get(room_id)

        if not room:
            return emit('error', {'msg': 'Sala inexistente'}, room=user_id)
        if room.password and room.password != pwd:
            return emit('error', {'msg': 'Contraseña incorrecta'}, room=user_id)

        count = Participant.query.filter_by(room_id=room_id).count()
        if count >= 2:
            return emit('error', {'msg': 'La sala ya está llena (2/2)'}, room=user_id)

        if not Participant.query.filter_by(room_id=room_id, user_id=user_id).first():
            db.session.add(Participant(room_id=room_id, user_id=user_id, username=username))
            db.session.commit()

        # 1) uno el socket al canal
        join_room(room_id)

        # 2) recalculo la lista
        participants = [p.username for p in room.participants]

        # 3) emito update_participants A TODA LA SALA
        emit('update_participants', {
            'participants': participants
        }, room=room_id)

        # 4) opcional: mensaje de sistema
        emit('server_message', {
            'msg': f"Usuario {username} se unió a la sala."
        }, room=room_id)

        # 5) refresco el lobby
        _broadcast_all(socketio)


    @socketio.on('leave_room')
    def handle_leave_room(data):
        user_id = request.sid
        room_id = data.get('room_id')

        # 1) Borro de la BD
        part = Participant.query.filter_by(room_id=room_id, user_id=user_id).first()
        if part:
            db.session.delete(part)
            db.session.commit()

        # 2) Recalculo la lista PARA quien queda
        participants = [p.username for p in Room.query.get(room_id).participants]
        print(f"[server] leave_room {room_id} pedido por {user_id}, quedan: {participants}")

        # 3) Emito actualización ANTES de sacar al socket del canal
        socketio.emit('update_participants', {
            'participants': participants
        }, room=room_id)

        # 4) Ahora sí saco el socket
        leave_room(room_id)

        # 5) Refresco el lobby global
        _broadcast_all(socketio)

    @socketio.on('delete_room')
    def handle_delete_room(data):
        room_id = data.get('room_id')
        print(f"[server] delete_room {room_id}")
        room = Room.query.get(room_id)
        if room:
            # notifico a todos los que estén EN ESA SALA que la borraron
            emit('room_deleted', {'room_id': room_id}, room=room_id)
            # borro de la DB
            db.session.delete(room)
            db.session.commit()
        # refresco el lobby en todos
        _broadcast_all(socketio)


def _broadcast_all(socketio):
    """Envía el rooms_list a todos los sockets conectados."""
    rooms = Room.query.filter_by(status='open').all()
    payload = [{
        'id': r.id,
        'name': r.name,
        'difficulty': r.difficulty,
        'hasPassword': bool(r.password),
        'count': Participant.query.filter_by(room_id=r.id).count(),
        'participants': [p.username for p in r.participants]
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
        'count': Participant.query.filter_by(room_id=r.id).count(),
        'participants': [ p.username for p in r.participants ]
    } for r in rooms]
    socketio.emit('rooms_list', {'rooms': payload}, room=sid)
