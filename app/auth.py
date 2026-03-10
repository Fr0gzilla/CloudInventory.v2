"""Authentification simple — un seul compte admin via .env, mot de passe hashé."""

import os
from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint("auth", __name__)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Veuillez vous connecter."
login_manager.login_message_category = "warning"


def _get_admin_password_hash():
    """Retourne le hash du mot de passe admin (hashé à la volée depuis .env)."""
    raw = os.getenv("ADMIN_PASSWORD", "admin")
    # Si la variable commence par un préfixe werkzeug, c'est déjà un hash
    if raw.startswith(("pbkdf2:", "scrypt:")):
        return raw
    return generate_password_hash(raw)


class User(UserMixin):
    """Utilisateur unique (pas de table DB)."""

    def __init__(self, username):
        self.id = username
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    if user_id == admin_username:
        return User(admin_username)
    return None


def _is_safe_redirect(target):
    """Vérifie que l'URL de redirection est relative (pas d'open redirect)."""
    if not target:
        return False
    parsed = urlparse(target)
    return parsed.scheme == "" and parsed.netloc == ""


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        pw_hash = _get_admin_password_hash()

        if username == admin_username and check_password_hash(pw_hash, password):
            login_user(User(admin_username))
            next_page = request.args.get("next")
            if not _is_safe_redirect(next_page):
                next_page = None
            return redirect(next_page or url_for("main.dashboard"))

        flash("Identifiants incorrects.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
