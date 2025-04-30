from database import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(255))
    url_image = db.Column(db.String(255))
    admin = db.Column(db.Boolean)
    level = db.Column(db.String(50))

class Reporte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_url = db.Column(db.String(255), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    size = db.Column(db.Float, nullable=False)
    elapsed_time = db.Column(db.String(50), nullable=True)
    title = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # revisar si .UTC va o si cambiamos a .utcnow

class TodosLosReportes(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Primary Key
    report_url = db.Column(db.String(255), unique=True, nullable=False)  # La URL del reporte
    title = db.Column(db.String(255), nullable=False)  # El título del reporte
    size_megabytes = db.Column(db.Float, nullable=True)  # El tamaño del reporte en megabytes, puede ser NULL si no está disponible
    created_at = db.Column(db.DateTime, nullable=True)  # La fecha de creación, puede ser NULL si no está disponible

class AllCommentsWithEvaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    archivo_binario = db.Column(db.LargeBinary)
# --------------------------------------------------------------------------------------------

class Room(db.Model):
    __tablename__ = 'rooms'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False) 
    host_user_id  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    difficulty    = db.Column(db.String(50), nullable=False)
    password      = db.Column(db.String(128), nullable=True)
    status        = db.Column(db.String(20), default='open')  # open / playing / closed
    participants  = db.relationship('Participant', back_populates='room', cascade='all, delete-orphan')

class Participant(db.Model):
    __tablename__ = 'participants'
    id        = db.Column(db.Integer, primary_key=True)
    room_id   = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'))
    ready     = db.Column(db.Boolean, default=False)
    retired   = db.Column(db.Boolean, default=False)
    username  = db.Column(db.String, nullable=False)
    room      = db.relationship('Room', back_populates='participants')


class Exercise(db.Model):
    __tablename__ = 'exercises'

    # PK incremental
    id =db.Column(db.Integer, primary_key=True)

    # Nivel: Fácil / Medio / Difícil
    level =db.Column(db.Enum('Fácil','Medio','Difícil', name='exercise_levels'), nullable=False)

    # Lenguaje: js / py
    language =db.Column(db.Enum('js','py', name='exercise_langs'), nullable=False)

    # Descripción / enunciado
    description =db.Column(db.Text, nullable=False)

    # Timestamps
    created_at =db.Column(db.DateTime, default=datetime.utcnow)
    updated_at =db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    matches = db.relationship('Match', back_populates='exercise')

    def serialize(self):
        return {
            'id': self.id,
            'level': self.level,
            'language': self.language,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Exercise {self.id} [{self.level}/{self.language}]>'


class Match(db.Model):
    __tablename__ = 'matches'

    # PK incremental
    id =db.Column(db.Integer, primary_key=True)

    # FK al ejercicio
    exercise_id =db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False)

    # Los dos jugadores
    player1_id =db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    player2_id =db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Soluciones que enviaron
    solution1 =db.Column(db.Text, nullable=True)
    solution2 =db.Column(db.Text, nullable=True)

    # Quién ganó
    winner_id =db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Justificación o output del comparador
    justification =db.Column(db.Text, nullable=True)

    # Tiempos: cuándo arrancó y terminó
    started_at =db.Column(db.DateTime, default=datetime.utcnow)
    finished_at =db.Column(db.DateTime, nullable=True)

    # Duración en segundos (calculable)
    duration_secs =db.Column(db.Integer, nullable=True)

    # Relaciones
    exercise = db.relationship('Exercise', back_populates='matches')
    player1 = db.relationship('User', foreign_keys=[player1_id])
    player2 = db.relationship('User', foreign_keys=[player2_id])
    winner  = db.relationship('User', foreign_keys=[winner_id])

    def serialize(self):
        return {
            'id': self.id,
            'exercise_id': self.exercise_id,
            'player1_id': self.player1_id,
            'player2_id': self.player2_id,
            'solution1': self.solution1,
            'solution2': self.solution2,
            'winner_id': self.winner_id,
            'justification': self.justification,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'duration_secs': self.duration_secs
        }

    def __repr__(self):
        return (
            f'<Match {self.id} Ex:{self.exercise_id} '
            f'P1:{self.player1_id} P2:{self.player2_id} Winner:{self.winner_id}>'
        )