from gevent import monkey
monkey.patch_all()
import os
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from database import db
from extensions import init_extensions
from routes.ejercicios_bp import ejercicios_bp
from routes.admin_bp import admin_bp
from routes.public_bp import public_bp
from routes.clasifica_comentarios_individuales_bp import clasifica_comentarios_individuales_bp


from models import User, Room, Participant
from dotenv import load_dotenv
from flask_socketio import SocketIO
from routes.socketio_bp import init_socketio  # nuevo módulo

load_dotenv()

app = Flask(__name__)

# Configuración Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
init_socketio(socketio)

# Extensiones
init_extensions(app)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"])

app.config["JWT_SECRET_KEY"] = os.getenv('JWT_SECRET_KEY', 'valor-variable')
app.config["JWT_TOKEN_LOCATION"]     = ["headers", "query_string"]
app.config["JWT_QUERY_STRING_NAME"]  = "token"
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# Blueprints HTTP
app.register_blueprint(admin_bp)
app.register_blueprint(public_bp, url_prefix='/public')
app.register_blueprint(clasifica_comentarios_individuales_bp, url_prefix='/')
app.register_blueprint(ejercicios_bp, url_prefix='/')

# Configuración DB
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'mydatabase.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if not os.path.exists(os.path.dirname(db_path)):
    os.makedirs(os.path.dirname(db_path))

with app.app_context():
    db.init_app(app)
    db.create_all()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)


# EJECUTO CON : Si es la primera vez en tu pc crea el entorno virtual e instala dependencias:

#                 python -m venv myenv
#                 pip install -r requirements.txt

#               Lo siguiente siempre para activar el entorno e iniciar el servidor:

#                 myenv\Scripts\activate       
#                 waitress-serve --port=5000 app:app