from flask import Blueprint, send_file, make_response, request, jsonify, render_template, current_app, Response # Blueprint para modularizar y relacionar con app
from flask_bcrypt import Bcrypt                                  # Bcrypt para encriptación
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity   # Jwt para tokens
from models import User, Exercise
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



ejercicios_bp = Blueprint('ejercicios_bp', __name__)     # instanciar admin_bp desde clase Blueprint para crear las rutas.

# Inicializamos herramientas de encriptado y access token ------------------------:

bcrypt = Bcrypt()
jwt = JWTManager()



# Ruta TEST------------------------------------------------
@ejercicios_bp.route('/test_ejercicios_bp', methods=['GET'])
def test():
    return jsonify({'message': 'test bien sucedido','status':"Si lees esto, el test de las rutas de ejercicio esta ok"}),200


@ejercicios_bp.route('/get_exercises', methods=['GET'])
@jwt_required()
def get_exercises():
    exercises = Exercise.query.all()
    return jsonify([e.serialize() for e in exercises]), 200

@ejercicios_bp.route('/create_exercise', methods=['POST'])
@jwt_required()
def create_exercise():
    data = request.get_json() or {}
    level       = data.get('level')
    language    = data.get('language')
    description = data.get('description')
    if not all([level, language, description]):
        return jsonify({'msg': 'Faltan campos: level, language o description'}), 400

    new_ex = Exercise(
        level=level,
        language=language,
        description=description
    )
    db.session.add(new_ex)
    db.session.commit()
    return jsonify(new_ex.serialize()), 201

@ejercicios_bp.route('/bulk_create_exercises', methods=['POST'])
@jwt_required()
def bulk_create_exercises():
    data = request.get_json() or []
    if not isinstance(data, list):
        return jsonify({'msg': 'Se esperaba un array de ejercicios'}), 400

    created = []
    errors = []
    for idx, item in enumerate(data):
        level = item.get('level')
        language = item.get('language')
        description = item.get('description')
        if not all([level, language, description]):
            errors.append({'index': idx, 'msg': 'Faltan campos level, language o description'})
            continue
        ex = Exercise(level=level, language=language, description=description)
        db.session.add(ex)
        created.append(ex)
    db.session.commit()

    return jsonify({
        'created': [e.serialize() for e in created],
        'errors': errors
    }), (400 if errors else 201)

@ejercicios_bp.route('/edit_exercise', methods=['PUT'])
@jwt_required()
def edit_exercise():
    data = request.get_json() or {}
    ex_id = data.get('id')
    if not ex_id:
        return jsonify({'msg': 'Falta el campo id'}), 400

    ex = Exercise.query.get(ex_id)
    if not ex:
        return jsonify({'msg': 'Ejercicio no encontrado'}), 404

    # Solo actualizamos los campos que vengan
    for attr in ('level', 'language', 'description'):
        if attr in data:
            setattr(ex, attr, data[attr])

    db.session.commit()
    return jsonify(ex.serialize()), 200

@ejercicios_bp.route('/delete_exercise', methods=['DELETE'])
@jwt_required()
def delete_exercise():
    data = request.get_json() or {}
    ex_id = data.get('id')
    if not ex_id:
        return jsonify({'msg': 'Falta el campo id'}), 400

    ex = Exercise.query.get(ex_id)
    if not ex:
        return jsonify({'msg': 'Ejercicio no encontrado'}), 404

    db.session.delete(ex)
    db.session.commit()
    return jsonify({'msg': 'Ejercicio eliminado'}), 200