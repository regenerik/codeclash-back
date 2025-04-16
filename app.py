import os # para saber la ruta absoluta de la db si no la encontramos
from flask_bcrypt import Bcrypt  # para encriptar y comparar
from flask import Flask, request, jsonify # Para endpoints
from flask_sqlalchemy import SQLAlchemy  # Para rutas
from flask_jwt_extended import  JWTManager
from routes.admin_bp import admin_bp                       # Acá importamos rutas admin
from routes.public_bp import public_bp                     # Acá importamos rutas public
from routes.clasifica_comentarios_individuales_bp import clasifica_comentarios_individuales_bp
from database import db                             # Acá importamos la base de datos inicializada
from flask_cors import CORS                         # Permisos de consumo
from extensions import init_extensions              # Necesario para que funcione el executor en varios archivos en simultaneo
from models import User                             # Importamos el modelo para TodosLosReportes
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# ↓↓↓ SOCKET.IO ↓↓↓
from flask_socketio import SocketIO, join_room, leave_room, emit
# uso eventlet como servidor WS
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
# ↑↑↑ FIN SOCKET.IO ↑↑↑


# Inicializa los extensiones
init_extensions(app)

CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True,allow_headers=["Content-Type", "Authorization"])

# ENCRIPTACION JWT y BCRYPT-------

app.config["JWT_SECRET_KEY"] = "valor-variable"  # clave secreta para firmar los tokens.( y a futuro va en un archivo .env)
jwt = JWTManager(app)  # isntanciamos jwt de JWTManager utilizando app para tener las herramientas de encriptacion.
bcrypt = Bcrypt(app)   # para encriptar password


# REGISTRAR BLUEPRINTS ( POSIBILIDAD DE UTILIZAR EL ENTORNO DE LA app EN OTROS ARCHIVOS Y GENERAR RUTAS EN LOS MISMOS )


app.register_blueprint(admin_bp)  # poder registrarlo como un blueprint ( parte del app )
                                                       # y si queremos podemos darle toda un path base como en el ejemplo '/admin'

app.register_blueprint(public_bp, url_prefix='/public')  # blueprint public_bp


app.register_blueprint(clasifica_comentarios_individuales_bp, url_prefix='/') # contiene ejemplos de executor y openai


# DATABASE---------------
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'mydatabase.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'


print(f"Ruta de la base de datos: {db_path}")


if not os.path.exists(os.path.dirname(db_path)): # Nos aseguramos que se cree carpeta instance automatico para poder tener mydatabase.db dentro.
    os.makedirs(os.path.dirname(db_path))



# Función para cargar los usuarios iniciales ( si necesitase )
def cargar_usuarios_iniciales():
    if User.query.count() == 0:  # Verificamos si la tabla User está vacía
        usuarios_iniciales = [
            {
                "email": os.getenv('EMAIL1'),
                "name": os.getenv('NAME1'),
                "password": os.getenv('PASSWORD1'),
                "dni": os.getenv('DNI1'),
                "admin": os.getenv('ADMIN1') == 'True',
                "url_image": os.getenv('URL_IMAGE1')
            },
            {
                "email": os.getenv('EMAIL2'),
                "name": os.getenv('NAME2'),
                "password": os.getenv('PASSWORD2'),
                "dni": os.getenv('DNI2'),
                "admin": os.getenv('ADMIN2') == 'True',
                "url_image": os.getenv('URL_IMAGE2')
            }
        ]

        for usuario in usuarios_iniciales:
            password_hash = bcrypt.generate_password_hash(usuario['password']).decode('utf-8')
            new_user = User(
                email=usuario['email'],
                name=usuario['name'],
                password=password_hash,
                dni=usuario['dni'],
                admin=usuario['admin'],
                url_image=usuario['url_image']
            )
            db.session.add(new_user)

        db.session.commit()
        print("Usuarios iniciales cargados correctamente.")


# ---------------------- SocketIO Events ----------------------

@socketio.on('connect')
def handle_connect():
    print(f">>> Cliente conectado: {request.sid}")
    emit('server_message', {'msg': 'Bienvenido al CodeClash!'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"<<< Cliente desconectado: {request.sid}")

@socketio.on('join_room')
def on_join(data):
    room = data.get('room_id')
    join_room(room)
    emit('server_message', {'msg': f"Usuario se unió a sala {room}"}, room=room)

@socketio.on('leave_room')
def on_leave(data):
    room = data.get('room_id')
    leave_room(room)
    emit('server_message', {'msg': f"Usuario salió de sala {room}"}, room=room)

# evento de chat genérico
@socketio.on('chat_message')
def handle_chat(data):
    room = data.get('room_id')
    msg  = data.get('msg')
    emit('chat_message', {'sid': request.sid, 'msg': msg}, room=room)

# --------------------------------------------------------------


with app.app_context():
    db.init_app(app)
    db.create_all() # Nos aseguramos que este corriendo en el contexto del proyecto.
    # cargar_usuarios_iniciales()
# -----------------------

# AL FINAL ( detecta que encendimos el servidor desde terminal y nos da detalles de los errores )
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)

# EJECUTO CON : Si es la primera vez en tu pc crea el entorno virtual e instala dependencias:

#                 python -m venv myenv
#                 pip install -r requirements.txt

#               Lo siguiente siempre para activar el entorno e iniciar el servidor:

#                 myenv\Scripts\activate       
#                 waitress-serve --port=5000 app:app