from flask import Blueprint, render_template, request, url_for, make_response
from sqlalchemy import func, and_
from extensions import db
from models.player import Player
from models.team import Team
from models.auction import AuctionEventLog
from models.squad import TeamSquad
import csv
import io

analytics_bp = Blueprint("analytics_bp", __name__, template_folder="../templates")

ROLE_OPTIONS = ["Batter", "Bowler", "All-Rounder", "Wicket Keeper"]


def get_team_spent(team_name):
    spent = db.session.query(func.coalesce(func.sum(TeamSquad.purchase_price), 0.0)).filter(TeamSquad.team_name == team_name).scalar()
    return float(spent or 0.0)


def get_team_squad_count(team_name):
    return db.session.query(func.count(TeamSquad.id)).filter(TeamSquad.team_name == team_name).scalar() or 0


def get_team_role_counts(team_name):
    results = db.session.query(TeamSquad.role, func.count(TeamSquad.id)).filter(TeamSquad.team_name == team_name).group_by(TeamSquad.role).all()
    return {role: count for role, count in results}


@analytics_bp.route("/dashboard")
def dashboard():
    total_sold = db.session.query(func.count(TeamSquad.id)).scalar() or 0
    total_unsold = db.session.query(func.count(Player.id)).filter(Player.status != "sold").scalar() or 0
    total_auction_value = db.session.query(func.coalesce(func.sum(TeamSquad.purchase_price), 0.0)).scalar() or 0.0
    average_sale_price = db.session.query(func.coalesce(func.avg(TeamSquad.purchase_price), 0.0)).scalar() or 0.0
    highest_sale_price = db.session.query(func.coalesce(func.max(TeamSquad.purchase_price), 0.0)).scalar() or 0.0
    lowest_sale_price = db.session.query(func.coalesce(func.min(TeamSquad.purchase_price), 0.0)).scalar() or 0.0

    top_purchases = TeamSquad.query.order_by(TeamSquad.purchase_price.desc()).limit(10).all()

    unsold_players_list = Player.query.filter_by(status="unsold").all()

    # Most competitive auction (player with most bids)
    bid_counts = db.session.query(
        AuctionEventLog.player_name, 
        func.count(AuctionEventLog.id).label('bids')
    ).filter(AuctionEventLog.event_type == "BID").group_by(AuctionEventLog.player_name).order_by(func.count(AuctionEventLog.id).desc()).first()
    
    most_competitive_auction = bid_counts[0] if bid_counts else "None"
    highest_bids_count = bid_counts[1] if bid_counts else 0

    team_list = Team.query.order_by(Team.team_name).all()
    team_analytics = []
    for team in team_list:
        spent = get_team_spent(team.team_name)
        initial_budget = round(team.budget + spent, 2)
        team_analytics.append({
            "team_name": team.team_name,
            "initial_budget": initial_budget,
            "remaining_budget": round(team.budget, 2),
            "spent": round(spent, 2),
            "squad_size": get_team_squad_count(team.team_name),
        })
    team_analytics.sort(key=lambda row: row["spent"], reverse=True)

    squad_sizes = db.session.query(TeamSquad.team_name, func.count(TeamSquad.id)).group_by(TeamSquad.team_name).all()
    squad_sizes = [{"team_name": name, "squad_size": count} for name, count in squad_sizes]

    role_counts_raw = db.session.query(TeamSquad.role, func.count(TeamSquad.id)).group_by(TeamSquad.role).all()
    role_distribution = {role: count for role, count in role_counts_raw}
    role_distribution = {
        "Batter": role_distribution.get("Batter", 0) + role_distribution.get("Batsman", 0),
        "Bowler": role_distribution.get("Bowler", 0),
        "All-Rounder": role_distribution.get("All-Rounder", 0),
        "Wicket Keeper": role_distribution.get("Wicket Keeper", 0),
    }

    leaderboard = []
    for team in team_list:
        purchased_players = Player.query.filter(Player.sold_to == team.team_name).all()
        ratings = [p.rating for p in purchased_players]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            roles = {p.role for p in purchased_players}
            balance_bonus = len(roles) * 5.0
            strength_score = round(avg_rating + balance_bonus, 2)
        else:
            avg_rating = 0.0
            strength_score = 0.0
        leaderboard.append({
            "team_name": team.team_name,
            "avg_rating": round(avg_rating, 2),
            "strength_score": strength_score,
        })
    leaderboard.sort(key=lambda row: row["strength_score"], reverse=True)

    performance = []
    for team in team_list:
        purchased = Player.query.filter(Player.sold_to == team.team_name).all()
        ratings = [p.rating for p in purchased]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
        total_spending = round(sum(p.sold_price or 0.0 for p in purchased), 2)
        spending_efficiency = round((avg_rating * len(purchased)) / total_spending, 2) if total_spending > 0 else 0.0
        performance.append({
            "team_name": team.team_name,
            "average_rating": avg_rating,
            "total_spending": total_spending,
            "spending_efficiency": spending_efficiency,
            "remaining_budget": round(team.budget, 2),
            "players_purchased": len(purchased),
        })

    return render_template(
        "dashboard.html",
        total_sold=total_sold,
        total_unsold=total_unsold,
        total_auction_value=round(total_auction_value, 2),
        average_sale_price=round(average_sale_price, 2),
        highest_sale_price=round(highest_sale_price, 2),
        lowest_sale_price=round(lowest_sale_price, 2),
        top_purchases=top_purchases,
        unsold_players_list=unsold_players_list,
        most_competitive_auction=most_competitive_auction,
        highest_bids_count=highest_bids_count,
        team_analytics=team_analytics,
        squad_sizes=squad_sizes,
        role_distribution=role_distribution,
        leaderboard=leaderboard,
        performance=performance,
    )


@analytics_bp.route("/dashboard/team/<team_name>")
def team_squad_detail(team_name):
    squad = TeamSquad.query.filter_by(team_name=team_name).order_by(TeamSquad.purchase_price.desc()).all()
    team = Team.query.filter_by(team_name=team_name).first()
    if not team:
        return render_template("team_squad.html", team_name=team_name, squad=[], error="Team not found.")

    return render_template("team_squad.html", team_name=team_name, squad=squad, team=team)


@analytics_bp.route("/auction-history")
def auction_history():
    team_filter = request.args.get("team", "")
    role_filter = request.args.get("role", "")
    min_price = request.args.get("min_price", "")
    max_price = request.args.get("max_price", "")

    query = AuctionEventLog.query.filter(AuctionEventLog.event_type == "SOLD")

    if team_filter:
        query = query.filter(AuctionEventLog.team_name == team_filter)

    if role_filter:
        query = query.join(
            TeamSquad,
            and_(AuctionEventLog.player_name == TeamSquad.player_name, AuctionEventLog.team_name == TeamSquad.team_name),
        ).filter(TeamSquad.role == role_filter)

    if min_price:
        try:
            query = query.filter(AuctionEventLog.amount >= float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            query = query.filter(AuctionEventLog.amount <= float(max_price))
        except ValueError:
            pass

    history = query.order_by(AuctionEventLog.timestamp.desc()).all()
    teams = Team.query.order_by(Team.team_name).all()

    return render_template(
        "auction_history.html",
        history=history,
        teams=teams,
        selected_team=team_filter,
        selected_role=role_filter,
        min_price=min_price,
        max_price=max_price,
        role_options=ROLE_OPTIONS,
    )


@analytics_bp.route("/export/<dataset>/<file_format>")
def export_data(dataset, file_format):
    file_format = file_format.lower()
    dataset = dataset.lower()
    output = io.StringIO()

    if dataset == "auction-results":
        rows = []
        events = AuctionEventLog.query.filter(AuctionEventLog.event_type == "SOLD").order_by(AuctionEventLog.timestamp.desc()).all()
        for event in events:
            squad = TeamSquad.query.filter_by(team_name=event.team_name, player_name=event.player_name).first()
            rows.append({
                "Player": event.player_name,
                "Team": event.team_name,
                "Role": squad.role if squad else "",
                "Sold Price": event.amount,
                "Timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M:%S") if event.timestamp else "",
            })
        filename = "auction_results"
        headers = ["Player", "Team", "Role", "Sold Price", "Timestamp"]
    elif dataset == "team-squads":
        rows = TeamSquad.query.order_by(TeamSquad.team_name, TeamSquad.purchase_price.desc()).all()
        filename = "team_squads"
        headers = ["Team", "Player", "Role", "Purchase Price"]
    else:
        return redirect(url_for("analytics_bp.dashboard"))

    if file_format == "csv":
        writer = csv.writer(output)
        writer.writerow(headers)
        if dataset == "team-squads":
            for row in rows:
                writer.writerow([row.team_name, row.player_name, row.role, row.purchase_price])
        else:
            for row in rows:
                writer.writerow([row[header] for header in headers])

        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
        response.headers["Content-Type"] = "text/csv"
        return response

    if file_format == "excel":
        html = ["<table border='1'><tr>"]
        for header in headers:
            html.append(f"<th>{header}</th>")
        html.append("</tr>")

        if dataset == "team-squads":
            for row in rows:
                html.append("<tr>")
                html.append(f"<td>{row.team_name}</td>")
                html.append(f"<td>{row.player_name}</td>")
                html.append(f"<td>{row.role}</td>")
                html.append(f"<td>{row.purchase_price}</td>")
                html.append("</tr>")
        else:
            for row in rows:
                html.append("<tr>")
                for header in headers:
                    html.append(f"<td>{row[header]}</td>")
                html.append("</tr>")

        html.append("</table>")
        response = make_response("".join(html))
        response.headers["Content-Disposition"] = f"attachment; filename={filename}.xls"
        response.headers["Content-Type"] = "application/vnd.ms-excel"
        return response

    return redirect(url_for("analytics_bp.dashboard"))
