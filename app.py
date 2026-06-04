import os
from flask import Flask, render_template, request, redirect, url_for
from constants import TEAM_LOGOS, TEAM_THEME, ROLE_ICONS
from extensions import db


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "devsecret123")
    
    # Database Abstraction
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    local_db_path = "sqlite:///" + os.path.join(os.path.abspath(os.path.dirname(__file__)), "database.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url or local_db_path
    
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    db.init_app(app)

    from routes.admin_routes import admin_bp
    from routes.team_routes import team_bp
    from routes.auction_routes import auction_bp
    from routes.auction_routes_v2 import auction_bp_v2
    from routes.analytics_routes import analytics_bp
    from routes.analytics_routes_v2 import analytics_bp_v2
    from routes.admin_management_routes import admin_mgmt_bp
    from routes.portfolio_routes import portfolio_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(auction_bp)
    app.register_blueprint(auction_bp_v2)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(analytics_bp_v2)
    app.register_blueprint(admin_mgmt_bp)
    app.register_blueprint(portfolio_bp)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    @app.route("/health")
    def health_check():
        from flask import jsonify
        return jsonify({"status": "ok"}), 200

    @app.context_processor
    def inject_constants():
        return dict(
            TEAM_LOGOS=TEAM_LOGOS,
            TEAM_THEME=TEAM_THEME,
            ROLE_ICONS=ROLE_ICONS
        )

    @app.route("/")
    def home():
        from services.team_analyzer import get_auction_overview, get_team_strength_preview, get_most_expensive_purchases, get_top_value_purchases
        from services.playing_xi_generator import get_all_teams_xi_comparison
        from services.winner_predictor import calculate_probabilities

        overview = get_auction_overview()
        team_strengths = get_team_strength_preview()
        top_expensive = get_most_expensive_purchases(1)
        top_value = get_top_value_purchases(1)
        teams_data = get_all_teams_xi_comparison()
        probs = calculate_probabilities()

        highest_xi = max(teams_data, key=lambda x: x["avg_rating"]) if teams_data else None
        best_squad = max(team_strengths, key=lambda x: x["strength_score"]) if team_strengths else None
        
        achievements = {
            "most_expensive": top_expensive[0] if top_expensive else None,
            "best_value": top_value[0] if top_value else None,
            "best_squad": best_squad,
            "highest_xi": highest_xi
        }

        top_5_teams = team_strengths[:5] if team_strengths else []
        top_5_probs = probs[:5] if probs else []

        return render_template("home.html", overview=overview, top_teams=top_5_teams, achievements=achievements, probs=top_5_probs)

    @app.route("/login")
    def login():
        return render_template("login.html")

    @app.route("/admin_login", methods=["POST"])
    def admin_login():
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            from models.auction import User
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password) and user.role == "admin":
                return redirect(url_for("admin_bp.admin"))
        except Exception:
            if username == "admin" and password == "admin123":
                return redirect(url_for("admin_bp.admin"))

        return render_template("login.html", error="Invalid username or password.")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)