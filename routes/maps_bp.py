from flask import Blueprint, send_file, make_response, request, jsonify, render_template, current_app, Response # Blueprint para modularizar y relacionar con app
from flask_bcrypt import Bcrypt                                  # Bcrypt para encriptación
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity   # Jwt para tokens
from models import User, TotalComents                            # importar tabla "User" de models
from database import db                                          # importa la db desde database.py
from datetime import timedelta                                   # importa tiempo especifico para rendimiento de token válido
from logging_config import logger
import os                                                        # Para datos .env
from dotenv import load_dotenv                                   # Para datos .env
load_dotenv()
import pandas as pd
import requests
from io import BytesIO




maps_bp = Blueprint('maps_bp', __name__)     # instanciar admin_bp desde clase Blueprint para crear las rutas.
bcrypt = Bcrypt()
jwt = JWTManager()

# Sistema de key base pre rutas ------------------------:

# API_KEY = os.getenv('API_KEY')

# def check_api_key(api_key):
#     return api_key == API_KEY

# @maps_bp.before_request
# def authorize():
#     if request.method == 'OPTIONS':
#         return
#     if request.path in ['/get_map_url','/test_maps_bp','/','/correccion_campos_vacios','/descargar_positividad_corregida','/download_comments_evaluation','/all_comments_evaluation','/download_resume_csv','/create_resumes_of_all','/descargar_excel','/create_resumes', '/reportes_disponibles', '/create_user', '/login', '/users','/update_profile','/update_profile_image','/update_admin']:
#         return
#     api_key = request.headers.get('Authorization')
#     if not api_key or not check_api_key(api_key):
#         return jsonify({'message': 'Unauthorized'}), 401
    
#--------------------------------RUTAS SINGLE---------------------------------

# Ruta de prueba time-out-test------------------------------------------------
@maps_bp.route('/test_maps_bp', methods=['GET'])
def test():
    return jsonify({'message': 'test bien sucedido','status':"Si lees esto, rutas de maps funcionan"}),200


@maps_bp.route('/get_map_url', methods=['POST'])
@jwt_required()
def get_map_url():
    try:
        logger.info("entro en la ruta get_map_url")
        # Obtener los datos enviados desde el frontend
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({"error": "URL no proporcionada"}), 400

        # Realizar la solicitud a la URL inicial
        response = requests.get(url)
        
        if response.status_code != 200:
            return jsonify({"error": f"Error al consultar la URL: {response.status_code}"}), response.status_code

        # Parsear la respuesta JSON
        json_data = response.json()

        if not json_data or not json_data[0].get('path') or not json_data[0].get('archivo'):
            return jsonify({"error": "Respuesta JSON no válida o incompleta"}), 400

        # Construir la URL final
        base_url = "https://storage.googleapis.com/mapoteca/"
        path = json_data[0]['path'].replace(" ", "%20")  # Codificar espacios
        archivo = json_data[0]['archivo']
        final_url = f"{base_url}{path}{archivo}"
        print("ESTA ES LA URL FINAL: ",final_url)
        # Devolver la URL final
        return jsonify({"url": final_url}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500