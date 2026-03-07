import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager  # [API] Authentification JWT pour l'API REST
from flasgger import Swagger                # [API] Documentation Swagger / OpenAPI
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///cloudinventory.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # [API] config de la clé secrète JWT
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", app.config["SECRET_KEY"])

    db.init_app(app)
    JWTManager(app)  # [API] Initialisation du JWT

    # [API] Documentation Swagger accessible sur /apidocs
    Swagger(app, template={
        "info": {
            "title": "CloudInventory API",
            "description": "API REST pour la gestion d'inventaire cloud (Proxmox + IPAM)",
            "version": "1.0.0",
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT token. Exemple : **Bearer &lt;token&gt;**",
            }
        },
    })

    from app.auth import auth_bp, login_manager
    login_manager.init_app(app)
    app.register_blueprint(auth_bp)

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # [API] Enregistrement du blueprint API REST (/api/...)
    from app.api import api_bp
    app.register_blueprint(api_bp)

    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()

    return app
