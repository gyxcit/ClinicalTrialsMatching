# src/routes/ui_favorites_routes.py
import requests
from flask import Blueprint, render_template, session, request, jsonify

favorites_bp = Blueprint("favorites", __name__)

def fetch_study_by_nct(nct: str):
    """
    Fetch a single study by NCT Id from clinicaltrials.gov API v2.
    Returns a dict shaped like other studies (with protocolSection), or None if error.
    """
    try:
        url = f"https://clinicaltrials.gov/api/v2/studies/{nct}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


@favorites_bp.get("/favorites")
def favorites():
    favs = session.get("favorites", [])
    fav_ids = set(favs)

    trials = session.get("trials", [])  # may exist if user visited /clinical-trials
    fav_trials = []

    # 1) Fast path: rebuild from trials in session
    if fav_ids and trials:
        for t in trials:
            ps = (t.get("protocolSection") or {})
            idm = (ps.get("identificationModule") or {})
            nct = (idm.get("nctId") or "")
            if nct and nct in fav_ids:
                fav_trials.append(t)

    # 2) Fallback: fetch each favorite via API v2
    if fav_ids and not fav_trials:
        for nct in favs:
            study = fetch_study_by_nct(nct)
            if study:
                fav_trials.append(study)
            else:
                # minimal fallback so template can render something
                fav_trials.append({
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": nct,
                            "briefTitle": "Saved clinical trial"
                        },
                        "statusModule": {"overallStatus": ""},
                        "designModule": {"phases": []},
                        "conditionsModule": {"conditions": []},
                        "sponsorCollaboratorsModule": {"leadSponsor": {"name": ""}}
                    }
                })

    return render_template(
        "favorites.html",
        layout="app",
        active_page="favorites",
        favorites=favs,
        fav_trials=fav_trials
    )


@favorites_bp.post("/api/favorites/toggle")
def api_toggle_favorite():
    data = request.get_json(silent=True) or {}
    nct = (data.get("nct") or data.get("nct_id") or "").strip()
    if not nct:
        return jsonify({"ok": False, "error": "Missing nct"}), 400

    favs = set(session.get("favorites", []))

    if nct in favs:
        favs.remove(nct)
        is_fav = False
    else:
        favs.add(nct)
        is_fav = True

    session["favorites"] = sorted(list(favs))
    session.modified = True

    return jsonify({
        "ok": True,
        "nct": nct,
        "is_favorite": is_fav,
        "count": len(favs)
    })
