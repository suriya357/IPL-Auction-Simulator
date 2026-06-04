from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models.player import Player
from models.team import Team

admin_bp = Blueprint("admin_bp", __name__, template_folder="../templates")


@admin_bp.route("/admin")
def admin():
    return render_template("admin.html")


@admin_bp.route("/players")
def players():
    players = Player.query.order_by(Player.name).all()
    return render_template("players.html", players=players)


@admin_bp.route("/players/add", methods=["GET", "POST"])
def add_player():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()
        base_price = request.form.get("base_price", "").strip()
        rating = request.form.get("rating", "").strip()
        errors = []

        if not name:
            errors.append("Player name is required.")
        if not role:
            errors.append("Player role is required.")
        try:
            base_price_value = float(base_price)
            if base_price_value <= 0:
                errors.append("Base price must be greater than 0.")
        except ValueError:
            errors.append("Base price must be a valid number.")

        try:
            rating_value = int(rating)
            if rating_value < 1 or rating_value > 100:
                errors.append("Rating must be between 1 and 100.")
        except ValueError:
            errors.append("Rating must be an integer.")

        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template("player_form.html", player={}, action="Add")

        player = Player(name=name, role=role, base_price=base_price_value, rating=rating_value)
        db.session.add(player)
        db.session.commit()
        flash("Player added successfully.", "success")
        return redirect(url_for("admin_bp.players"))

    return render_template("player_form.html", player={}, action="Add")


@admin_bp.route("/players/edit/<int:player_id>", methods=["GET", "POST"])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()
        base_price = request.form.get("base_price", "").strip()
        rating = request.form.get("rating", "").strip()
        errors = []

        if not name:
            errors.append("Player name is required.")
        if not role:
            errors.append("Player role is required.")
        try:
            base_price_value = float(base_price)
            if base_price_value <= 0:
                errors.append("Base price must be greater than 0.")
        except ValueError:
            errors.append("Base price must be a valid number.")

        try:
            rating_value = int(rating)
            if rating_value < 1 or rating_value > 100:
                errors.append("Rating must be between 1 and 100.")
        except ValueError:
            errors.append("Rating must be an integer.")

        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template("player_form.html", player=player, action="Edit")

        player.name = name
        player.role = role
        player.base_price = base_price_value
        player.rating = rating_value
        db.session.commit()
        flash("Player updated successfully.", "success")
        return redirect(url_for("admin_bp.players"))

    return render_template("player_form.html", player=player, action="Edit")


@admin_bp.route("/players/delete/<int:player_id>")
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    db.session.delete(player)
    db.session.commit()
    flash("Player deleted successfully.", "success")
    return redirect(url_for("admin_bp.players"))


@admin_bp.route("/teams")
def teams():
    teams = Team.query.order_by(Team.team_name).all()
    return render_template("teams.html", teams=teams)


@admin_bp.route("/teams/add", methods=["GET", "POST"])
def add_team():
    if request.method == "POST":
        team_name = request.form.get("team_name", "").strip()
        budget = request.form.get("budget", "").strip()
        errors = []

        if not team_name:
            errors.append("Team name is required.")
        try:
            budget_value = float(budget)
            if budget_value <= 0:
                errors.append("Budget must be greater than 0.")
        except ValueError:
            errors.append("Budget must be a valid number.")

        if Team.query.filter_by(team_name=team_name).first():
            errors.append("A team with that name already exists.")

        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template("team_form.html", team={}, action="Add")

        team = Team(team_name=team_name, budget=budget_value)
        db.session.add(team)
        db.session.commit()
        flash("Team added successfully.", "success")
        return redirect(url_for("admin_bp.teams"))

    return render_template("team_form.html", team={}, action="Add")


@admin_bp.route("/teams/edit/<int:team_id>", methods=["GET", "POST"])
def edit_team(team_id):
    team = Team.query.get_or_404(team_id)
    if request.method == "POST":
        team_name = request.form.get("team_name", "").strip()
        budget = request.form.get("budget", "").strip()
        errors = []

        if not team_name:
            errors.append("Team name is required.")
        try:
            budget_value = float(budget)
            if budget_value <= 0:
                errors.append("Budget must be greater than 0.")
        except ValueError:
            errors.append("Budget must be a valid number.")

        existing_team = Team.query.filter_by(team_name=team_name).first()
        if existing_team and existing_team.id != team.id:
            errors.append("Another team with that name already exists.")

        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template("team_form.html", team=team, action="Edit")

        team.team_name = team_name
        team.budget = budget_value
        db.session.commit()
        flash("Team updated successfully.", "success")
        return redirect(url_for("admin_bp.teams"))

    return render_template("team_form.html", team=team, action="Edit")


@admin_bp.route("/teams/delete/<int:team_id>")
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    db.session.delete(team)
    db.session.commit()
    flash("Team deleted successfully.", "success")
    return redirect(url_for("admin_bp.teams"))
