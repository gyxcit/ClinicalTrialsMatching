from flask import Blueprint, render_template, request, redirect, url_for, session

home_bp = Blueprint("home", __name__)

@home_bp.get("/")
def home():
    return render_template("home.html", layout="landing", active_page="home")

@home_bp.post("/set-mode")
def set_mode():
    mode = request.form.get("mode", "patient")
    session["mode"] = mode
    return redirect(url_for("patient.patient_profile"))  # <- note le prefix blueprint
