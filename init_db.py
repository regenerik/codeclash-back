# init_db.py

import os
from flask import Flask
from database import db

def create_app_minimal():
    app = Flask(__name__)
    # copiá exactamente la URI que usa tu app.py
    db_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        'instance',
        'mydatabase.db'
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

if __name__ == '__main__':
    app = create_app_minimal()
    with app.app_context():
        # Importá *todos* tus modelos acá, DESPUÉS de init_app,
        # para que queden registrados en db.metadata
        from models import (
            User, Reporte, TodosLosReportes,
            AllCommentsWithEvaluation, Room, Participant
        )
        # Ahora sí creá todo
        db.create_all()
        print("🗄️  Base de datos reseteada y actualizada con Users, Reporte, Room y Participant")
