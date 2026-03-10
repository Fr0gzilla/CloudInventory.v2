import logging
import os
from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager  # [API] Authentification JWT pour l'API REST
from flasgger import Swagger                # [API] Documentation Swagger / OpenAPI
from dotenv import load_dotenv

load_dotenv()

APP_VERSION = "2.1"

db = SQLAlchemy()

# Logging applicatif
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cloudinventory")


def create_app():
    app = Flask(__name__)

    # Sécurité : SECRET_KEY obligatoire en production
    secret = os.getenv("SECRET_KEY", "")
    if not secret or secret == "change-me":
        if not app.debug and not app.testing:
            logger.warning("SECRET_KEY non définie ou par défaut — à changer en production !")
        secret = secret or "dev-only-insecure-key"
    app.config["SECRET_KEY"] = secret

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///cloudinventory.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # PER_PAGE centralisé
    app.config["PER_PAGE"] = int(os.getenv("PER_PAGE", "25"))

    # [API] config de la clé secrète JWT + expiration explicite
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", app.config["SECRET_KEY"])
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        hours=int(os.getenv("JWT_EXPIRATION_HOURS", "1"))
    )

    db.init_app(app)
    JWTManager(app)  # [API] Initialisation du JWT

    # [API] Documentation Swagger accessible sur /apidocs
    Swagger(app, template={
        "info": {
            "title": "CloudInventory API",
            "description": "API REST pour la gestion d'inventaire cloud (Proxmox + IPAM)",
            "version": APP_VERSION,
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

    app.jinja_env.globals["APP_VERSION"] = APP_VERSION

    # Webhook de notification des anomalies
    app.config["WEBHOOK_URL"] = os.getenv("WEBHOOK_URL", "")

    # Notification email SMTP
    app.config["SMTP_ENABLED"] = os.getenv("SMTP_ENABLED", "false").lower() == "true"
    app.config["SMTP_HOST"] = os.getenv("SMTP_HOST", "localhost")
    app.config["SMTP_PORT"] = int(os.getenv("SMTP_PORT", "587"))
    app.config["SMTP_USE_TLS"] = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    app.config["SMTP_USERNAME"] = os.getenv("SMTP_USERNAME", "")
    app.config["SMTP_PASSWORD"] = os.getenv("SMTP_PASSWORD", "")
    app.config["SMTP_FROM"] = os.getenv("SMTP_FROM", "cloudinventory@localhost")
    app.config["SMTP_TO"] = os.getenv("SMTP_TO", "")

    # Context processor : injecte le compteur d'anomalies du dernier run dans tous les templates
    @app.context_processor
    def inject_anomaly_badge():
        from app.models import Run, Anomaly
        last_run = Run.query.order_by(Run.id.desc()).first()
        if last_run:
            count = Anomaly.query.filter_by(run_id=last_run.id).count()
            return {"navbar_anomaly_count": count, "navbar_last_run_id": last_run.id}
        return {"navbar_anomaly_count": 0, "navbar_last_run_id": None}

    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()

    # ── Commandes CLI Flask ──
    _register_cli_commands(app)

    return app


def _register_cli_commands(app):
    """Enregistre les commandes CLI personnalisées (flask run-inventory, flask purge-runs)."""
    import click

    @app.cli.command("run-inventory")
    def cli_run_inventory():
        """Lancer un inventaire depuis la ligne de commande."""
        with app.app_context():
            from collector.inventory_runner import run_inventory
            run = run_inventory()
            click.echo(f"Run #{run.id} — {run.status} "
                        f"({run.vm_count} VMs, {run.matched_name_count} matched)")

    @app.cli.command("purge-runs")
    @click.option("--keep", default=30, help="Nombre de runs à conserver")
    def cli_purge_runs(keep):
        """Supprimer les anciens runs (conserve les N derniers)."""
        with app.app_context():
            from app.models import Run, ConsolidatedAsset, Anomaly
            all_runs = Run.query.order_by(Run.id.desc()).all()
            to_delete = all_runs[keep:]
            deleted = 0
            for run in to_delete:
                Anomaly.query.filter_by(run_id=run.id).delete()
                ConsolidatedAsset.query.filter_by(run_id=run.id).delete()
                db.session.delete(run)
                deleted += 1
            db.session.commit()
            click.echo(f"{deleted} runs supprimés (conservé les {keep} derniers)")
