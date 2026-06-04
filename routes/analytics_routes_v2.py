import io
import csv
from flask import Blueprint, render_template, Response, session, redirect, url_for, request
from services.team_analyzer import (
    get_auction_overview,
    get_team_spending_analytics,
    get_top_value_purchases,
    get_most_expensive_purchases,
    get_role_distribution,
    get_team_strength_preview,
    get_advanced_efficiency_metrics
)
from services.playing_xi_generator import generate_playing_xi, get_all_teams_xi_comparison
from services.winner_predictor import (
    calculate_probabilities,
    project_league_table,
    run_season_simulation,
    predict_matchup,
    generate_insights
)
from models.player import Player
from models.team import Team
from models.squad import TeamSquad

try:
    import openpyxl
    from openpyxl import Workbook
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

analytics_bp_v2 = Blueprint("analytics_bp_v2", __name__, template_folder="../templates")

@analytics_bp_v2.route("/dashboard/v2")
def dashboard_v2():
    overview = get_auction_overview()
    team_spending = get_team_spending_analytics()
    top_value = get_top_value_purchases(10)
    top_expensive = get_most_expensive_purchases(10)
    role_dist = get_role_distribution()
    strength_preview = get_team_strength_preview()
    efficiency = get_advanced_efficiency_metrics()
    
    teams_data = get_all_teams_xi_comparison()
    best_squad = max(strength_preview, key=lambda x: x["strength_score"]) if strength_preview else None
    highest_xi = max(teams_data, key=lambda x: x["avg_rating"]) if teams_data else None
    best_bowling = max(teams_data, key=lambda x: x["bowling_strength"]) if teams_data else None
    
    achievements = {
        "most_expensive": top_expensive[0] if top_expensive else None,
        "best_value": top_value[0] if top_value else None,
        "best_squad": best_squad,
        "highest_xi": highest_xi,
        "best_bowling": best_bowling
    }
    
    return render_template(
        "dashboard_v2.html",
        overview=overview,
        team_spending=team_spending,
        top_value=top_value,
        top_expensive=top_expensive,
        role_dist=role_dist,
        strength_preview=strength_preview,
        efficiency=efficiency,
        achievements=achievements
    )

@analytics_bp_v2.route("/team-analysis/<team_name>")
def team_analysis(team_name):
    # Get team analytics
    squad = TeamSquad.query.filter_by(team_name=team_name).all()
    team = Team.query.filter_by(team_name=team_name).first()
    
    if not team:
        return redirect(url_for('analytics_bp_v2.dashboard_v2'))
        
    role_dist = get_role_distribution().get(team_name, {})
    strengths = get_team_strength_preview()
    strength_score = next((s for s in strengths if s["team_name"] == team_name), None)
    
    # Enrich squad with player data
    player_names = [p.player_name for p in squad]
    players_data = Player.query.filter(Player.name.in_(player_names)).all()
    players_dict = {p.name: p for p in players_data}
    
    enriched_squad = []
    for s in squad:
        p_data = players_dict.get(s.player_name)
        enriched_squad.append({
            "name": s.player_name,
            "role": s.role,
            "price": s.purchase_price,
            "rating": p_data.rating if p_data else 0
        })
        
    # Sort top players by rating
    top_players = sorted(enriched_squad, key=lambda x: x["rating"], reverse=True)[:5]
    
    return render_template(
        "team_analysis.html",
        team_name=team_name,
        team=team,
        squad=enriched_squad,
        role_dist=role_dist,
        strength_score=strength_score,
        top_players=top_players
    )

@analytics_bp_v2.route("/export/csv/<dataset>")
def export_csv(dataset):
    si = io.StringIO()
    writer = csv.writer(si)
    
    if dataset == "results":
        writer.writerow(["Player Name", "Role", "Rating", "Base Price", "Sold Price", "Sold To", "Status"])
        players = Player.query.order_by(Player.sold_price.desc()).all()
        for p in players:
            writer.writerow([p.name, p.role, p.rating, p.base_price, p.sold_price, p.sold_to, p.status])
            
    elif dataset == "squads":
        writer.writerow(["Team Name", "Player Name", "Role", "Purchase Price"])
        squads = TeamSquad.query.order_by(TeamSquad.team_name, TeamSquad.purchase_price.desc()).all()
        for s in squads:
            writer.writerow([s.team_name, s.player_name, s.role, s.purchase_price])
            
    elif dataset == "summary":
        writer.writerow(["Team Name", "Players Purchased", "Total Spend", "Remaining Budget", "Average Rating", "Budget Utilization %", "Strength Score"])
        spending = get_team_spending_analytics()
        strengths = get_team_strength_preview()
        strength_dict = {s["team_name"]: s["strength_score"] for s in strengths}
        
        for sp in spending:
            writer.writerow([
                sp["team_name"],
                sp["players_purchased"],
                sp["total_spend"],
                sp["remaining_budget"],
                sp["avg_rating"],
                sp["utilization"],
                strength_dict.get(sp["team_name"], 0)
            ])
            
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=auction_{dataset}.csv"}
    )

@analytics_bp_v2.route("/export/xlsx/<dataset>")
def export_xlsx(dataset):
    if not EXCEL_AVAILABLE:
        return "Excel export requires openpyxl. Use CSV export instead.", 400
        
    wb = Workbook()
    ws = wb.active
    ws.title = dataset.capitalize()
    
    if dataset == "results":
        ws.append(["Player Name", "Role", "Rating", "Base Price", "Sold Price", "Sold To", "Status"])
        players = Player.query.order_by(Player.sold_price.desc()).all()
        for p in players:
            ws.append([p.name, p.role, p.rating, p.base_price, p.sold_price, p.sold_to or "", p.status])
            
    elif dataset == "squads":
        ws.append(["Team Name", "Player Name", "Role", "Purchase Price"])
        squads = TeamSquad.query.order_by(TeamSquad.team_name, TeamSquad.purchase_price.desc()).all()
        for s in squads:
            ws.append([s.team_name, s.player_name, s.role, s.purchase_price])
            
    elif dataset == "summary":
        ws.append(["Team Name", "Players Purchased", "Total Spend", "Remaining Budget", "Average Rating", "Budget Utilization %", "Strength Score"])
        spending = get_team_spending_analytics()
        strengths = get_team_strength_preview()
        strength_dict = {s["team_name"]: s["strength_score"] for s in strengths}
        
        for sp in spending:
            ws.append([
                sp["team_name"],
                sp["players_purchased"],
                sp["total_spend"],
                sp["remaining_budget"],
                sp["avg_rating"],
                sp["utilization"],
                strength_dict.get(sp["team_name"], 0)
            ])
            
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename=auction_{dataset}.xlsx"}
    )

@analytics_bp_v2.route("/playing-xi")
def playing_xi_comparison():
    teams_data = get_all_teams_xi_comparison()
    return render_template("playing_xi.html", comparison=teams_data)

@analytics_bp_v2.route("/playing-xi/<team_name>")
def playing_xi_team(team_name):
    data = generate_playing_xi(team_name)
    return render_template("playing_xi.html", team_data=data, team_name=team_name)

@analytics_bp_v2.route("/predictor")
def winner_predictor():
    probs = calculate_probabilities()
    table = project_league_table()
    insights = generate_insights()
    return render_template("winner_predictor.html", probs=probs, table=table, insights=insights)

@analytics_bp_v2.route("/simulator", methods=["GET", "POST"])
def season_simulator():
    results = None
    iterations = 100
    volatility = "Medium"
    
    if request.method == "POST":
        iterations = int(request.form.get("iterations", 100))
        volatility = request.form.get("volatility", "Medium")
        results = run_season_simulation(iterations, volatility)
        
    return render_template("season_simulation.html", results=results, iterations=iterations, volatility=volatility)

@analytics_bp_v2.route("/matchup", methods=["GET", "POST"])
def matchup_predictor():
    teams_query = Team.query.order_by(Team.team_name).all()
    ipl_teams = [t.team_name for t in teams_query]
    
    matchup = None
    if request.method == "POST":
        team_a = request.form.get("team_a")
        team_b = request.form.get("team_b")
        if team_a and team_b and team_a != team_b:
            matchup = predict_matchup(team_a, team_b)
            
    return render_template("matchup.html", teams=ipl_teams, matchup=matchup)

@analytics_bp_v2.route("/compare-teams", methods=["GET", "POST"])
def compare_teams():
    teams_query = Team.query.order_by(Team.team_name).all()
    ipl_teams = [t.team_name for t in teams_query]
    
    comparison = None
    if request.method == "POST":
        team_a = request.form.get("team_a")
        team_b = request.form.get("team_b")
        
        if team_a and team_b and team_a != team_b:
            teams_data = get_all_teams_xi_comparison()
            data_a = next((t for t in teams_data if t["team_name"] == team_a), None)
            data_b = next((t for t in teams_data if t["team_name"] == team_b), None)
            
            spending = get_team_spending_analytics()
            spend_a = next((t for t in spending if t["team_name"] == team_a), None)
            spend_b = next((t for t in spending if t["team_name"] == team_b), None)
            
            dist = get_role_distribution()
            dist_a = dist.get(team_a, {})
            dist_b = dist.get(team_b, {})
            
            if data_a and data_b and spend_a and spend_b:
                comparison = {
                    "a": {
                        "name": team_a,
                        "budget": spend_a["remaining_budget"],
                        "squad_size": spend_a["players_purchased"],
                        "avg_rating": spend_a["avg_rating"],
                        "xi_rating": data_a["avg_rating"],
                        "batters": dist_a.get("Batter", {}).get("count", 0) + dist_a.get("Batsman", {}).get("count", 0),
                        "bowlers": dist_a.get("Bowler", {}).get("count", 0),
                        "all_rounders": dist_a.get("All-Rounder", {}).get("count", 0),
                        "wks": dist_a.get("Wicket Keeper", {}).get("count", 0)
                    },
                    "b": {
                        "name": team_b,
                        "budget": spend_b["remaining_budget"],
                        "squad_size": spend_b["players_purchased"],
                        "avg_rating": spend_b["avg_rating"],
                        "xi_rating": data_b["avg_rating"],
                        "batters": dist_b.get("Batter", {}).get("count", 0) + dist_b.get("Batsman", {}).get("count", 0),
                        "bowlers": dist_b.get("Bowler", {}).get("count", 0),
                        "all_rounders": dist_b.get("All-Rounder", {}).get("count", 0),
                        "wks": dist_b.get("Wicket Keeper", {}).get("count", 0)
                    }
                }
                
    return render_template("team_comparison.html", teams=ipl_teams, comparison=comparison)

@analytics_bp_v2.route("/power-rankings")
def power_rankings():
    probs = calculate_probabilities()
    return render_template("power_rankings.html", rankings=probs)
