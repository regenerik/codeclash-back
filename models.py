from database import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'
    dni = db.Column(db.String(50))
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(255))
    url_image = db.Column(db.String(255))
    admin = db.Column(db.Boolean)

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