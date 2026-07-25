import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Débogueur Werkzeug désactivé par défaut (RCE si exposé) et écoute en loopback.
    # Pour un accès réseau, servir via gunicorn (jamais ce serveur de dev).
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    app.run(debug=debug, host=host, port=5050)
