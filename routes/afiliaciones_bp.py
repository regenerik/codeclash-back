from flask import Blueprint, send_file, make_response, request, jsonify, render_template, current_app, Response # Blueprint para modularizar y relacionar con app
from flask_bcrypt import Bcrypt                                  # Bcrypt para encriptación
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity   # Jwt para tokens
from logging_config import logger
import os                                                        # Para datos .env
from dotenv import load_dotenv                                   # Para datos .env
load_dotenv()
import requests
from bs4 import BeautifulSoup
import os
import logging



afiliaciones_bp = Blueprint('afiliaciones_bp', __name__)     # instanciar admin_bp desde clase Blueprint para crear las rutas.
bcrypt = Bcrypt()
jwt = JWTManager()

# Sistema de key base pre rutas ------------------------:

# API_KEY = os.getenv('API_KEY')

# def check_api_key(api_key):
#     return api_key == API_KEY

# @afiliaciones_bp.before_request
# def authorize():
#     if request.method == 'OPTIONS':
#         return
#     if request.path in ['/test_afiliaciones','/consulta-afiliado',]:
#         return
#     api_key = request.headers.get('Authorization')
#     if not api_key or not check_api_key(api_key):
#         return jsonify({'message': 'Unauthorized'}), 401
    
# RUTA TEST:

@afiliaciones_bp.route('/test_afiliaciones', methods=['GET'])
def test():
    return jsonify({'message': 'test bien sucedido','status':"Si lees esto las rutas de afiliaciones andan bien..."}),200




# ------------------------------------------------




logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@afiliaciones_bp.route("/consulta-afiliado", methods=["POST"])
@jwt_required()
def consultar_afiliacion():
    try:
        data = request.json
        clave_elector = data.get('clave_elector')
        apellido_paterno = data.get('apellido_paterno')
        apellido_materno = data.get('apellido_materno')
        nombre = data.get('nombre')

        # Validar inputs
        if not all([clave_elector, apellido_paterno, apellido_materno, nombre]):
            return jsonify({"error": "Faltan datos para realizar la consulta."}), 400

        session = requests.Session()

        # Paso 1: Obtener la página inicial
        url_inicial = "https://deppp-partidos.ine.mx/afiliadosPartidos/app/publico/consultaAfiliados/nacionales?execution=e1s1"
        response = session.get(url_inicial)
        if response.status_code != 200:
            raise Exception("Error al acceder a la página inicial")

        # Extraer el `javax.faces.ViewState`
        soup = BeautifulSoup(response.text, 'lxml')
        viewstate_input = soup.find('input', {'name': 'javax.faces.ViewState'})
        viewstate = viewstate_input['value'] if viewstate_input else None
        if not viewstate:
            raise Exception("No se encontró el ViewState en la página inicial")

        # Paso 2: Enviar el formulario
        form_data = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "form:btnConsultarDetalle",
            "javax.faces.partial.execute": "form form:btnConsultarDetalle",
            "javax.faces.partial.render": "form form:pnlDetalleAfiliado form:pnlDetalleAfiliadoNoEncontrado",
            "form:btnConsultarDetalle": "form:btnConsultarDetalle",
            "form": "form",
            "form:inputClaveElector": clave_elector,
            "form:inputAPaterno": apellido_paterno,
            "form:inputAMaterno": apellido_materno,
            "form:inputNombre": nombre,
            "javax.faces.ViewState": viewstate,
        }
        response = session.post(url_inicial, data=form_data)
        if response.status_code != 200:
            raise Exception("Error al enviar el formulario")

        # Analizar la respuesta para determinar el flujo
        soup = BeautifulSoup(response.text, 'lxml')

        # Caso 1: No pertenece a ningún partido político
        detalle_no_encontrado = soup.find("div", {"id": "form:pnlDetalleAfiliadoNoEncontrado_content"})
        if detalle_no_encontrado:
            mensaje = f"La persona {nombre} {apellido_paterno} {apellido_materno} no pertenece actualmente a ningún partido político vigente."
            return jsonify({"msg": mensaje})

        # Caso 2: Pertenece a un partido político
        detalle_afiliado = soup.find("div", {"id": "form:pnlDetalleAfiliado_content"})
        if detalle_afiliado:
            logger.info("Caso positivo detectado. Analizando información...")

            # Extraer el nombre
            nombre_persona = detalle_afiliado.find("label", {"style": "color: black; font-size: x-large;"})
            nombre = nombre_persona.text.strip() if nombre_persona else None
            logger.info(f"Nombre detectado: {nombre}")

            # Extraer la entidad
            entidad_div = detalle_afiliado.find("div", {"class": "thumbnail"})
            entidad_label = entidad_div.find_next("label") if entidad_div else None
            entidad = entidad_label.text.strip() if entidad_label else None
            logger.info(f"Entidad detectada: {entidad}")

            # Extraer el partido político
            partido_div = detalle_afiliado.find_all("div", {"class": "thumbnail"})[1]
            partido_label = partido_div.find("label") if partido_div else None
            partido = partido_label.text.strip() if partido_label else None
            logger.info(f"Partido detectado: {partido}")

            # Extraer la fecha de afiliación
            fecha_div = detalle_afiliado.find_all("div", {"class": "thumbnail"})[2]
            fecha_label = fecha_div.find("label") if fecha_div else None
            fecha_afiliacion = fecha_label.text.strip() if fecha_label else None
            logger.info(f"Fecha de afiliación detectada: {fecha_afiliacion}")

            # Verificar que todos los datos sean válidos
            if not (nombre and entidad and partido and fecha_afiliacion):
                logger.error("Error al extraer información. Algunos datos están incompletos.")
                logger.error(detalle_afiliado.prettify())
                raise Exception("Error al extraer la información del caso positivo.")

            nombre_limpio = " ".join(nombre.split())
            # Crear el mensaje final
            mensaje = (
                f"La persona {nombre_limpio} de la entidad {entidad} "
                f"pertenece al: {partido}. Fecha de afiliación: {fecha_afiliacion}."
            )
            return jsonify({"msg": mensaje})


        # Caso no identificado
        return jsonify({"error": "La lógica para este caso aún está en construcción."}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500