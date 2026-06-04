from flask import Blueprint, render_template, session, flash, redirect, url_for
from extensions import db
from models.player import Player
from models.team import Team
from models.auction import AuctionResult, AuctionEventLog
from models.squad import TeamSquad
from models.ai_engine import (
    calculate_interest_score,
    should_ai_bid,
    get_bid_increment,
    TEAM_PERSONALITIES,
)
import uuid

auction_bp = Blueprint("auction_bp", __name__, template_folder="../templates")

IPL_TEAMS = ["CSK", "MI", "RCB", "KKR", "SRH", "DC", "GT", "PBKS", "RR", "LSG"]


def get_current_player():
    player_ids = session.get("auction_player_ids", [])
    index = session.get("current_index", 0)
    if index is None or index >= len(player_ids):
        return None
    return Player.query.get(player_ids[index])


def initialize_auction_state(human_team):
    player_ids = [p.id for p in Player.query.filter_by(status="available").order_by(Player.rating.desc(), Player.base_price.desc()).all()]
    session["auction_player_ids"] = player_ids
    session["current_index"] = 0
    session["auction_id"] = str(uuid.uuid4())
    session["current_bid"] = Player.query.get(player_ids[0]).base_price if player_ids else 0
    session["highest_bidder"] = None
    session["auction_finished"] = False
    session["ai_teams"] = [t for t in IPL_TEAMS if t != human_team]
    session["event_log"] = []
    session["ai_passed"] = []


def log_event(event_type, team_name, player_name=None, amount=None):
    event = {
        "event_type": event_type,
        "team_name": team_name,
        "player_name": player_name,
        "amount": amount,
    }
    events = session.get("event_log", [])
    events.insert(0, event)
    session["event_log"] = events[:20]
    session.modified = True

    db.session.add(AuctionEventLog(
        auction_id=session.get("auction_id", ""),
        event_type=event_type,
        team_name=team_name,
        player_name=player_name,
        amount=amount,
    ))
    db.session.commit()


def advance_to_next_player():
    player_ids = session.get("auction_player_ids", [])
    current_index = session.get("current_index", 0) + 1
    session["current_index"] = current_index
    if current_index >= len(player_ids):
        session["auction_finished"] = True
        return None
    next_player = Player.query.get(player_ids[current_index])
    session["current_bid"] = next_player.base_price
    session["highest_bidder"] = None
    session["ai_passed"] = []
    session.modified = True
    return next_player


def run_ai_bidding_round():
    selected_team = session.get("selected_team")
    player = get_current_player()
    if not player or not selected_team:
        return

    ai_teams = session.get("ai_teams", [])
    ai_passed = set(session.get("ai_passed", []))
    current_bid = session.get("current_bid", player.base_price)
    highest_bidder = session.get("highest_bidder")

    for ai_team in ai_teams:
        if ai_team in ai_passed:
            continue

        team = Team.query.filter_by(team_name=ai_team).first()
        if not team or team.budget <= current_bid:
            ai_passed.add(ai_team)
            log_event("AI_PASS", ai_team, player.name)
            continue

        interest_score = calculate_interest_score(ai_team, player)
        if should_ai_bid(interest_score):
            increment = get_bid_increment(current_bid)
            next_bid = round(current_bid + increment, 2)

            if next_bid <= team.budget:
                session["current_bid"] = next_bid
                session["highest_bidder"] = ai_team
                log_event("AI_BID", ai_team, player.name, next_bid)
                session.modified = True
            else:
                ai_passed.add(ai_team)
                log_event("AI_PASS", ai_team, player.name)
        else:
            ai_passed.add(ai_team)
            log_event("AI_PASS", ai_team, player.name)

    session["ai_passed"] = list(ai_passed)
    session.modified = True




@auction_bp.route("/auction")
def auction():
    selected_team = session.get("selected_team")
    if not selected_team:
        flash("Please select a team before joining the auction.", "warning")
        return redirect(url_for("team_bp.select_team"))

    if "auction_player_ids" not in session:
        initialize_auction_state(selected_team)

    if session.get("auction_finished"):
        return render_template("auction_complete.html", selected_team=selected_team)

    player = get_current_player()
    if not player:
        session["auction_finished"] = True
        return render_template("auction_complete.html", selected_team=selected_team)

    team = Team.query.filter_by(team_name=selected_team).first()
    squad = TeamSquad.query.filter_by(team_name=selected_team).all()
    teams = Team.query.order_by(Team.team_name).all()
    event_log = session.get("event_log", [])

    return render_template(
        "auction.html",
        selected_team=selected_team,
        player=player,
        current_bid=session.get("current_bid", player.base_price),
        highest_bidder=session.get("highest_bidder"),
        team=team,
        squad=squad,
        teams=teams,
        event_log=event_log,
    )


@auction_bp.route("/bid", methods=["POST"])
def bid():
    selected_team = session.get("selected_team")
    if not selected_team:
        flash("Please select a team before bidding.", "warning")
        return redirect(url_for("team_bp.select_team"))

    player = get_current_player()
    if not player:
        flash("No player available for bidding.", "warning")
        return redirect(url_for("auction_bp.auction"))

    current_bid = session.get("current_bid", player.base_price)
    increment = get_bid_increment(current_bid)
    next_bid = round(current_bid + increment, 2)

    team = Team.query.filter_by(team_name=selected_team).first()
    if not team or next_bid > team.budget:
        flash("Insufficient budget to raise the bid.", "danger")
        return redirect(url_for("auction_bp.auction"))

    session["current_bid"] = next_bid
    session["highest_bidder"] = selected_team
    session["ai_passed"] = []
    log_event("BID", selected_team, player.name, next_bid)
    session.modified = True

    run_ai_bidding_round()

    return redirect(url_for("auction_bp.auction"))


@auction_bp.route("/pass", methods=["POST"])
def pass_bid():
    selected_team = session.get("selected_team")
    if not selected_team:
        flash("Please select a team before passing.", "warning")
        return redirect(url_for("team_bp.select_team"))

    player = get_current_player()
    if not player:
        flash("No player available to pass.", "warning")
        return redirect(url_for("auction_bp.auction"))

    log_event("PASS", selected_team, player.name)
    session["ai_passed"] = [selected_team]
    session.modified = True

    run_ai_bidding_round()

    highest_bidder = session.get("highest_bidder")
    if highest_bidder:
        sale_price = session.get("current_bid", player.base_price)
        winning_team = Team.query.filter_by(team_name=highest_bidder).first()

        if winning_team and sale_price <= winning_team.budget:
            player.status = "sold"
            player.sold_price = sale_price
            player.sold_to = highest_bidder
            winning_team.budget -= sale_price

            db.session.add(player)
            db.session.add(winning_team)
            db.session.add(AuctionResult(player_name=player.name, team_name=highest_bidder, sold_price=sale_price))
            db.session.add(TeamSquad(team_name=highest_bidder, player_name=player.name, role=player.role, purchase_price=sale_price))
            db.session.commit()

            log_event("SOLD", highest_bidder, player.name, sale_price)
            flash(f"Player sold to {highest_bidder} for {sale_price:.2f} Cr.", "success")
        else:
            log_event("UNSOLD", highest_bidder, player.name, sale_price)
            flash("Player could not be sold due to budget constraint.", "warning")
    else:
        log_event("UNSOLD", "N/A", player.name)
        flash("No bids received. Player passed.", "info")

    advance_to_next_player()
    return redirect(url_for("auction_bp.auction"))


@auction_bp.route("/squad")
def squad():
    selected_team = session.get("selected_team")
    if not selected_team:
        flash("Please select your team first.", "warning")
        return redirect(url_for("team_bp.select_team"))

    squad = TeamSquad.query.filter_by(team_name=selected_team).all()
    team = Team.query.filter_by(team_name=selected_team).first()
    teams = Team.query.order_by(Team.team_name).all()
    return render_template("squad.html", selected_team=selected_team, squad=squad, team=team, teams=teams)
