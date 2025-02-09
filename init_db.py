# Si queres resetear el contenido de la db o la re estructuraste:
# 1 - Eliminas el archivo en la carpeta mydatabase.db que esta en instance
# 2 - Ejecutás en la consola ( posicionado en la base del proyecto y con el env encendido ): python init_db.py
# 3 - Si en render, tu db esta en un disco pagado aparte, vas a tener que resetearlo para que sufra cambios ( ver docs de render )

from database import db
from app import app
from models import Reporte, User  # Importa todos los modelos necesarios

# Crear las tablas en la base de datos
with app.app_context():
    db.create_all()
    print("Base de datos actualizada.")
