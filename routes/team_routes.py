from flask import Blueprint, render_template, request, redirect, url_for, session, flash

team_bp = Blueprint("team_bp", __name__, template_folder="../templates")

IPL_TEAMS = [
    "CSK",
    "MI",
    "RCB",
    "KKR",
    "SRH",
    "DC",
    "GT",
    "PBKS",
    "RR",
    "LSG",
]


@team_bp.route("/select-team", methods=["GET", "POST"])
def select_team():
    if request.method == "POST":
        selected_team = request.form.get("team_name")
        if selected_team not in IPL_TEAMS:
            flash("Please select a valid team.", "danger")
            return render_template("select_team.html", teams=IPL_TEAMS)

        session["selected_team"] = selected_team
        flash(f"{selected_team} selected as your team.", "success")
        return redirect(url_for("auction_bp_v2.auction"))

    return render_template("select_team.html", teams=IPL_TEAMS)
