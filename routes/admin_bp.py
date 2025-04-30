from flask import Blueprint, send_file, make_response, request, jsonify, render_template, current_app, Response # Blueprint para modularizar y relacionar con app
from flask_bcrypt import Bcrypt                                  # Bcrypt para encriptación
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity   # Jwt para tokens
from models import User                                          # importar tabla "User" de models
from database import db                                          # importa la db desde database.py
from datetime import timedelta                                   # importa tiempo especifico para rendimiento de token válido
from logging_config import logger                                # logger.info("console log que se ve en render")
import os                                                        # Para datos .env
from dotenv import load_dotenv                                   # Para datos .env
load_dotenv()                                                    # Para datos .env
import pandas as pd                                              # Para modificar tablas
from io import BytesIO                                           # Transformar archivos base 64
#imports para investigar contido de un html específico:
import requests
from bs4 import BeautifulSoup
#------------------------------------------------------



admin_bp = Blueprint('admin', __name__)     # instanciar admin_bp desde clase Blueprint para crear las rutas.

# Inicializamos herramientas de encriptado y access token ------------------------:

bcrypt = Bcrypt()
jwt = JWTManager()

# Sistema de key base pre rutas ------------------------:

# API_KEY = os.getenv('API_KEY')

# def check_api_key(api_key):
#     return api_key == API_KEY

# @admin_bp.before_request
# def authorize():
#     if request.method == 'OPTIONS':
#         return
#     # En la lista de este if agregamos las rutas que no querramos restringir si no tienen el API_KEY embutido en Authorization en HEADERS.
#     if request.path in ['/test_admin_bp','/','/correccion_campos_vacios','/descargar_positividad_corregida','/download_comments_evaluation','/all_comments_evaluation','/download_resume_csv','/create_resumes_of_all','/descargar_excel','/create_resumes', '/reportes_disponibles', '/create_user', '/login', '/users','/update_profile','/update_profile_image','/update_admin']:
#         return
#     api_key = request.headers.get('Authorization')
#     if not api_key or not check_api_key(api_key):
#         return jsonify({'message': 'Unauthorized'}), 401
    
#--------------------------------RUTAS SINGLE---------------------------------



# Ruta TEST------------------------------------------------
@admin_bp.route('/test_admin_bp', methods=['GET'])
def test():
    return jsonify({'message': 'test bien sucedido','status':"Si lees esto, tenemos que ver como manejar el timeout porque los archivos llegan..."}),200

# RUTA DOCUMENTACION
@admin_bp.route('/', methods=['GET'])
def show_hello_world():
         return render_template('instructions.html')

# RUTAS DE ADMINISTRACIÓN DE USUARIOS Y ADMINS ---------------------------------------------------------------

    # RUTA CREAR USUARIO
@admin_bp.route('/create_user', methods=['POST'])
def create_user():
    try:
        email = request.json.get('email')
        password = request.json.get('password')
        name = request.json.get('nickname')
        admin = False
        url_image = "base url"

        if not email or not password or not name:
            return jsonify({'error': 'email, password, and name are required.'}), 400

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'Email already exists.'}), 409

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')


        # Ensamblamos el usuario nuevo
        new_user = User(email=email, password=password_hash, name=name , admin=admin, url_image=url_image)

        db.session.add(new_user)
        db.session.commit()

        good_to_share_to_user = {
            'name':new_user.name,
            'email':new_user.email,
            'admin':new_user.admin,
            'url_image':new_user.url_image
        }

        return jsonify({'message': 'User created successfully.','user_created':good_to_share_to_user}), 201

    except Exception as e:
        return jsonify({'error': 'Error in user creation: ' + str(e)}), 500


    #RUTA LOG-IN ( CON TOKEN DE RESPUESTA )
@admin_bp.route('/login', methods=['POST'])
def get_token():
    try:
        #  Primero chequeamos que por el body venga la info necesaria:
        email = request.json.get('email')
        password = request.json.get('password')

        if not email or not password:
            return jsonify({'error': 'Email y password son requeridos.'}), 400
        
        # Buscamos al usuario con ese correo electronico ( si lo encuentra lo guarda ):
        login_user = User.query.filter_by(email=request.json['email']).one()

        # Verificamos que el password sea correcto:
        password_from_db = login_user.password #  Si loguin_user está vacio, da error y se va al "Except".
        true_o_false = bcrypt.check_password_hash(password_from_db, password)
        
        # Si es verdadero generamos un token y lo devuelve en una respuesta JSON:
        if true_o_false:
            expires = timedelta(minutes=30)  # pueden ser "hours", "minutes", "days","seconds"

            user_id = login_user.id       # recuperamos el id del usuario para crear el token...
            access_token = create_access_token(identity=user_id, expires_delta=expires)   # creamos el token con tiempo vencimiento
            return jsonify({ 'access_token':access_token, 'name':login_user.name, 'admin':login_user.admin, 'email':login_user.email, 'url_image':login_user.url_image}), 200  # Enviamos el token al front ( si es necesario serializamos el "login_user" y tambien lo enviamos en el objeto json )

        else:
            return {"Error":"Contraseña  incorrecta"}
    
    except Exception as e:
        return {"Error":"El email proporcionado no corresponde a ninguno registrado: " + str(e)}, 500
    

    # EJEMPLO DE RUTA RESTRINGIDA POR TOKEN. ( LA MISMA RECUPERA TODOS LOS USERS Y LO ENVIA PARA QUIEN ESTÉ LOGUEADO )
@admin_bp.route('/users')
@jwt_required()  # Decorador para requerir autenticación con JWT
def show_users():
    current_user_dni = get_jwt_identity()  # Obtiene la id del usuario del token
    if current_user_dni:
        users = User.query.all()
        user_list = []
        for user in users:
            user_dict = {
                'email': user.email,
                'name': user.name,
                'admin': user.admin,
                'url_image': user.url_image
            }
            user_list.append(user_dict)
        return jsonify({"lista_usuarios":user_list , 'cantidad':len(user_list)}), 200
    else:
        return {"Error": "Token inválido o vencido"}, 401

    # ACTUALIZAR PERFIL
@admin_bp.route('/update_profile', methods=['PUT'])
def update():
    email = request.json.get('email')
    password = request.json.get('password')
    name = request.json.get('name')
    url_image = "base"


    # Verificar que todos los campos requeridos estén presentes
    if not email or not password or not name or not url_image:
        return jsonify({"error": "Todos los campos son obligatorios"}), 400

    # Buscar al usuario por email
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Actualizar los datos del usuario
    user.name = name
    user.password = bcrypt.generate_password_hash(password)  # Asegúrate de hash la contraseña antes de guardarla
    user.url_image = url_image

    try:
        db.session.commit()
        return jsonify({"message": "Usuario actualizado con éxito"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al actualizar el usuario: {str(e)}"}), 500
    

    # ACTUALIZAR IMAGEN DE PERFIL
@admin_bp.route('/update_profile_image', methods=['PUT'])
def update_profile_image():
    email = request.json.get('email')
    url_image = request.json.get('url_image')

    # Verificar que ambos campos estén presentes
    if not email or not url_image:
        return jsonify({"error": "El email y la URL de la imagen son obligatorios"}), 400

    # Buscar al usuario por email
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Actualizar solo la URL de la imagen
    user.url_image = url_image

    try:
        db.session.commit()
        return jsonify({"message": "Imagen de perfil actualizada con éxito"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al actualizar la imagen: {str(e)}"}), 500
    
    # ACTUALIZAR CONDICIÓN DE ADMIN
@admin_bp.route('/update_admin', methods=['PUT'])
def update_admin():
    email = request.json.get('email')
    admin = request.json.get('admin')

    # Verificar que ambos campos estén presentes
    if email is None or admin is None:
        return jsonify({"error": "El email y la situación admin son obligatorios"}), 400

    # Buscar al usuario por email
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Actualizar estado admin
    user.admin = not user.admin

    try:
        db.session.commit()
        return jsonify({"message": f"Estado admin de {email} ahora es {'admin' if user.admin else 'no admin'}", "admin": user.admin}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al actualizar el estado admin: {str(e)}"}), 500
    
    # OBTENER USUARIO POR SU DNI
@admin_bp.route('/get_user/<int:id>', methods=['GET'])
def get_user(id):
    try:
        
        login_user = User.query.filter_by(id=id).one()

        if login_user:
            return jsonify({'name':login_user.name, 'admin':login_user.admin, 'email':login_user.email, 'url_image':login_user.url_image}), 200 

        else:
            return {"Error":"No se encontró un usuario con ese documento"}
    
    except Exception as e:
        return {"Error":"El dni proporcionado no corresponde a ninguno registrado: " + str(e)}, 500
    
@admin_bp.route('/user_update', methods=['PATCH'])
@jwt_required()
def update_user():
    # 1) Tomás el ID del token
    user_id = get_jwt_identity()
    # 2) Buscás el usuario en la DB
    user = User.query.get(user_id)
    if not user:
        return jsonify({'msg': 'Usuario no encontrado'}), 404

    # 3) Leé la prop (o props) que vienen en el JSON
    data = request.get_json() or {}
    # Ejemplo: { "email": "nuevo@mail.com" }
    # 4) Reemplazás el valor en el modelo
    for field, new_value in data.items():
        if hasattr(user, field):
            setattr(user, field, new_value)

    # 5) Commit de la sesión
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'Error al guardar cambios', 'error': str(e)}), 500

    # 6) Devuelves el usuario actualizado (para que tu action lo reciba)
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.name,
            'email': user.email,
            'name': user.name,
            'level': user.level,
            'url_image': user.url_image
        }
    }), 200


@admin_bp.route('/update-password', methods=['PATCH'])
@jwt_required()
def update_password():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'msg': 'Usuario no encontrado'}), 404

    data = request.get_json() or {}
    old_pass = data.get('old_password')
    new_pass = data.get('new_password')

    # Verificar contraseña actual
    if not bcrypt.check_password_hash(user.password, old_pass):
        return jsonify({'msg': 'La contraseña actual no coincide'}), 401

    # Actualizar y guardar
    user.password = bcrypt.generate_password_hash(new_pass)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'Error al guardar nueva contraseña', 'error': str(e)}), 500

    # Opcional: devolvés user sin el hash si lo necesitás
    return jsonify({'msg': 'Contraseña actualizada correctamente'}), 200


@admin_bp.route('/validate-token', methods=['GET'])
@jwt_required()  
def validate_token():

    current_user = get_jwt_identity()
    return jsonify(valid=True, user=current_user), 200