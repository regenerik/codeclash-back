from flask import Blueprint, send_file, make_response, request, jsonify, render_template, current_app, Response # Blueprint para modularizar y relacionar con app
from flask_bcrypt import Bcrypt                                  # Bcrypt para encriptación
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity   # Jwt para tokens
from models import EstadisticaFederal2024, EstadisticaLocal2024 
from database import db                                          # importa la db desde database.py
from datetime import timedelta                                   # importa tiempo especifico para rendimiento de token válido
from logging_config import logger
import os                                                        # Para datos .env
from dotenv import load_dotenv                                   # Para datos .env
load_dotenv()
import pandas as pd
import requests
from io import BytesIO
from federal_data import datos_electorales_fed
from local_data import datos_electorales_loc





estadisticas_bp = Blueprint('estadisticas_bp', __name__)     # instanciar admin_bp desde clase Blueprint para crear las rutas.
bcrypt = Bcrypt()
jwt = JWTManager()

# Sistema de key base pre rutas ------------------------:

API_KEY = os.getenv('API_KEY')

def check_api_key(api_key):
    return api_key == API_KEY

@estadisticas_bp.before_request
def authorize():
    if request.method == 'OPTIONS':
        return
    if request.path in ['/ver-registros-federal','/resultados_electorales','/subir-excel', '/test_estadisticas_bp','/','/correccion_campos_vacios','/descargar_positividad_corregida','/download_comments_evaluation','/all_comments_evaluation','/download_resume_csv','/create_resumes_of_all','/descargar_excel','/create_resumes', '/reportes_disponibles', '/create_user', '/login', '/users','/update_profile','/update_profile_image','/update_admin']:
        return
    api_key = request.headers.get('Authorization')
    if not api_key or not check_api_key(api_key):
        return jsonify({'message': 'Unauthorized'}), 401
    
#--------------------------------RUTAS SINGLE---------------------------------

# Ruta de prueba time-out-test------------------------------------------------
@estadisticas_bp.route('/test_estadisticas_bp', methods=['GET'])
def test():
    return jsonify({'message': 'test bien sucedido','status':"Si lees esto, rutas de estadisticas funcionan"}),200

@estadisticas_bp.route('/resultados_electorales', methods=['POST'])
def procesar_registro():
    try:
        logger.info("1 - Entró en la ruta /resultados_electorales. Recuperando datos necesarios...")
        
        # Validar entrada
        data = request.get_json()
        if not data or 'registro' not in data or 'ambito' not in data:
            return jsonify({"error": "Datos incompletos"}), 400
        
        logger.info("2 - Información validada. Separando info...")
        registro = data['registro']
        ambito = data['ambito']

        # Verificar ámbito y seleccionar datos
        if ambito == "federal":
            datos_electorales = datos_electorales_fed
        elif ambito == "local":
            datos_electorales = datos_electorales_loc
        else:
            return jsonify({"error": "Ámbito inválido"}), 400

        logger.info(f"3 - Usando datos para el ámbito: {ambito}. Buscando registro...")

        # Buscar el registro en el diccionario
        registro_objeto = datos_electorales.get(registro)
        if not registro_objeto:
            return jsonify({"error": "Registro no encontrado"}), 404

        logger.info(f"4 - Registro encontrado: {registro_objeto}")

        # Devolver el objeto completo
        return jsonify({"registro_completo": registro_objeto}), 200

    except Exception as e:
        logger.error(f"Error en la ruta /resultados_electorales: {e}")
        return jsonify({"error": str(e)}), 500


@estadisticas_bp.route('/subir-excel', methods=['POST'])
def subir_excel():
    logger.info("1 - Entró en la ruta /subir-excel. Validando la existencia del archivo entrante...")
    try:
        # Validar que se suba un archivo
        if 'file' not in request.files:
            return jsonify({"error": "No se envió ningún archivo"}), 400

        archivo = request.files['file']

        logger.info("2 - Archivo serparado con éxito. Determinando si es federal o local...")

        # Determinar si el archivo es "federal" o "local"
        nombre_archivo = archivo.filename.lower()
        if 'federal' in nombre_archivo:
            Model = EstadisticaFederal2024
        elif 'local' in nombre_archivo:
            Model = EstadisticaLocal2024
        else:
            return jsonify({"error": "El nombre del archivo debe contener 'federal' o 'local'"}), 400

        logger.info(f"3 - La tabla seleccionada es {Model}. Codificando a binario...")

        # Leer los datos binarios del archivo
        contenido_binario = archivo.read()

        logger.info("4 - Eliminando registros anteriores y guardando el nuevo...")

        # Reemplazar el registro existente o crear uno nuevo
        registro_existente = Model.query.first()
        if registro_existente:
            registro_existente.archivo = contenido_binario
        else:
            nuevo_registro = Model(archivo=contenido_binario)
            db.session.add(nuevo_registro)

        # Guardar los cambios en la base de datos
        db.session.commit()

        logger.info("5 - Archivo nuevo guardado en la tabla. Fin del proceso.")

        return jsonify({"message": f"Archivo {nombre_archivo} guardado exitosamente en la tabla correspondiente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


