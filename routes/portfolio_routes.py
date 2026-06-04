from flask import Blueprint, render_template

portfolio_bp = Blueprint("portfolio_bp", __name__, template_folder="../templates", url_prefix="/portfolio")

@portfolio_bp.route("/about")
def about():
    return render_template("portfolio_about.html")

@portfolio_bp.route("/architecture")
def architecture():
    return render_template("portfolio_architecture.html")

@portfolio_bp.route("/tech-stack")
def tech_stack():
    return render_template("portfolio_tech_stack.html")

@portfolio_bp.route("/changelog")
def changelog():
    return render_template("portfolio_changelog.html")
