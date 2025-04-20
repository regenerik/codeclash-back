# routes/socketio_bp.py
from flask import request
from flask_socketio import emit, join_room, leave_room
from database import db
from models import Room, Participant
from threading import Timer

room_states = {}

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
            # borrás todos los participantes de este user
            for p in parts:
                db.session.delete(p)
            db.session.commit()

            # por cada sala de la que salió, avisás a esa sala (string)
            for rid in room_ids:
                participants = [
                    p.username
                    for p in Room.query.get(rid).participants
                ]
                socketio.emit(
                    'update_participants',
                    {'participants': participants},
                    room=str(rid)       # <- ojo, str(rid) en vez de int
                )

            # y refrescás el lobby general
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
        # Estado inicial: 5 min y nadie listo
        room_states[str(room.id)] = {'timer': 5, 'ready': {}, 'countdown': False}
        # Avisamos al host su timer por defecto
        emit('timer_updated', {'minutes': 5}, room=str(room.id))

        emit('room_created', {
            'id': room.id,
            'roomName': room.name,
            'difficulty': room.difficulty,
            'participants': [username]
        }, room=user_id)

        _broadcast_all(socketio)

    @socketio.on('change_timer')
    def handle_change_timer(data):
        rid = str(data.get('room_id'))
        minutes = data.get('minutes')
        state = room_states.setdefault(rid, {'timer': minutes, 'ready': {}, 'countdown': False})
        state['timer'] = minutes
        emit('timer_updated', {'minutes': minutes}, room=rid)

    @socketio.on('toggle_ready')
    def handle_toggle_ready(data):
        rid = str(data.get('room_id'))
        uid = request.sid
        ready = data.get('ready')

        # Estado de la sala con soporte para cancelar el timer
        state = room_states.setdefault(rid, {
            'timer': None,
            'ready': {},
            'countdown': False,
            'countdown_timer': None
        })

        # Guardar estado de ready
        state['ready'][uid] = ready

        # Sacar el username
        p = Participant.query.filter_by(room_id=rid, user_id=uid).first()
        uname = p.username if p else 'Anon'

        # Avisar al room del cambio de ready
        emit('ready_updated', {'username': uname, 'ready': ready}, room=rid)

        # Si ya había un countdown y alguien se desmarca, lo cancelamos
        if state['countdown'] and not ready:
            state['countdown'] = False
            t = state.get('countdown_timer')
            if t:
                t.cancel()
                state['countdown_timer'] = None
            emit('cancel_countdown', {}, room=rid)

        # Chequear si hay dos jugadores y ambos listos
        parts = Participant.query.filter_by(room_id=rid).all()
        if len(parts) == 2 and all(state['ready'].get(p.user_id) for p in parts):
            # Arrancamos el conteo
            state['countdown'] = True
            emit('start_countdown', {'seconds': 5}, room=rid)

            # Programamos el inicio real en 5 segundos
            def do_start():
                st = room_states.get(rid)
                # Si nadie canceló
                if st and st.get('countdown'):
                    emit('game_started', {}, room=rid)
                    st['countdown'] = False
                    st['countdown_timer'] = None

            t = Timer(5, do_start)
            state['countdown_timer'] = t
            t.start()

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

    @socketio.on('update_code')
    def handle_update_code(data):
        rid  = str(data.get('room_id'))
        user = data.get('username')
        code = data.get('code')
        # Emití a todos (incluido quien mandó) – podés ajustar include_self si querés
        emit('code_updated', {'username': user, 'code': code}, room=rid)

    @socketio.on('submit_solution')
    def handle_submit_solution(data):
        rid   = str(data.get('room_id'))
        user  = data.get('username')
        code  = data.get('code')
        # Guardamos en memoria (o DB) la solución
        state = room_states.setdefault(rid, {})
        sols  = state.setdefault('solutions', {})
        sols[user] = code

        # Si ambos participantes ya entregaron, avisamos
        participants = Participant.query.filter_by(room_id=rid).all()
        if len(participants) == 2 and all(p.username in sols for p in participants):
            # Mandamos todas las soluciones a la sala
            emit('both_finished', {'solutions': sols}, room=rid)

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
