"""Authentification simple — un seul compte admin via .env."""

import os
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user

auth_bp = Blueprint("auth", __name__)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Veuillez vous connecter."
login_manager.login_message_category = "warning"


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


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")

        if username == admin_username and password == admin_password:
            login_user(User(admin_username))
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))

        flash("Identifiants incorrects.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
