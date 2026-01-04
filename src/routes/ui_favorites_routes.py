from flask import Blueprint, render_template, session

favorites_bp = Blueprint("favorites", __name__)

@favorites_bp.get("/favorites")
def favorites():
    favs = session.get("favorites", [])
    return render_template(
        "favorites.html",
        layout="app",
        active_page="favorites",
        favorites=favs
    )
