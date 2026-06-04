from flask import Blueprint, render_template, session, flash, redirect, url_for, jsonify, request
from extensions import db
from models.player import Player
from models.team import Team
from models.auction import AuctionResult, AuctionEventLog
from models.squad import TeamSquad
from models.auction_session import AuctionSession
from models.ai_engine_v2 import (
    calculate_interest_score,
    should_team_bid,
    calculate_maximum_bid,
    can_team_join_auction,
    get_bid_increment,
    get_team_squad_composition,
    MIN_SQUAD_SIZE,
    MAX_SQUAD_SIZE,
)
from datetime import datetime, timedelta
import uuid
import json

auction_bp_v2 = Blueprint("auction_bp_v2", __name__, template_folder="../templates")

IPL_TEAMS = ["CSK", "MI", "RCB", "KKR", "SRH", "DC", "GT", "PBKS", "RR", "LSG"]
COUNTDOWN_DURATION = 2  # seconds per countdown stage
MAX_EVENT_LOG = 50


def get_current_player():
    auction = AuctionSession.query.filter_by(auction_id=session.get("auction_id", "")).first()
    if auction and auction.current_player_id:
        return Player.query.get(auction.current_player_id)
    return None


def initialize_auction_session():
    """Initialize a new auction session with event-driven model."""
    player_ids = [
        p.id
        for p in Player.query.filter_by(status="available")
        .order_by(Player.rating.desc(), Player.base_price.desc())
        .all()
    ]
    
    if not player_ids:
        return None
    
    auction_id = str(uuid.uuid4())
    first_player = Player.query.get(player_ids[0])
    
    auction = AuctionSession(
        auction_id=auction_id,
        current_player_id=first_player.id,
        auction_stage="ROUND_1",
        auction_state="OPEN",
        current_bid=first_player.base_price,
        highest_bidder=None,
    )
    db.session.add(auction)
    db.session.commit()
    
    session["auction_id"] = auction_id
    session["auction_player_ids"] = player_ids
    session["current_index"] = 0
    session["event_log"] = []
    session.modified = True
    
    return auction


def log_event(event_type, details=None):
    """Log auction event for display and persistence."""
    event = {
        "event_type": event_type,
        "details": details or "",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    events = session.get("event_log", [])
    events.insert(0, event)
    session["event_log"] = events[:MAX_EVENT_LOG]
    session.modified = True
    
    auction_id = session.get("auction_id", "")
    player = get_current_player()
    
    db.session.add(
        AuctionEventLog(
            auction_id=auction_id,
            event_type=event_type,
            team_name=details.get("team_name", "") if isinstance(details, dict) else "",
            player_name=player.name if player else "",
            amount=details.get("amount") if isinstance(details, dict) else None,
        )
    )
    db.session.commit()


def advance_to_next_player():
    """Move to next player in auction."""
    current_index = session.get("current_index", 0) + 1
    player_ids = session.get("auction_player_ids", [])
    
    auction = AuctionSession.query.filter_by(auction_id=session.get("auction_id", "")).first()

    if current_index >= len(player_ids):
        if auction and getattr(auction, "auction_stage", "ROUND_1") == "ROUND_1":
            unsold_players = Player.query.filter_by(status="unsold").order_by(Player.rating.desc(), Player.base_price.desc()).all()
            if unsold_players:
                auction.auction_stage = "ACCELERATED_ROUND"
                player_ids = [p.id for p in unsold_players]
                session["auction_player_ids"] = player_ids
                session["current_index"] = 0
                for p in unsold_players:
                    p.status = "available"
                db.session.commit()
                log_event("SYSTEM", {"details": "Starting Accelerated Round"})
                current_index = 0
            else:
                if auction:
                    auction.auction_stage = "COMPLETED"
                    db.session.commit()
                session["auction_finished"] = True
                return None
        else:
            if auction:
                auction.auction_stage = "COMPLETED"
                db.session.commit()
            session["auction_finished"] = True
            return None
    
    next_player = Player.query.get(player_ids[current_index])
    
    auction = AuctionSession.query.filter_by(auction_id=session.get("auction_id", "")).first()
    if auction:
        auction.current_player_id = next_player.id
        auction.auction_state = "OPEN"
        auction.current_bid = next_player.base_price
        auction.highest_bidder = None
        auction.last_bid_timestamp = datetime.utcnow()
        auction.countdown_started = None
        auction.teams_passed = ""
        auction.teams_interested = ""
        db.session.commit()
    
    session["current_index"] = current_index
    session.modified = True
    
    return next_player


def get_interested_teams(player):
    """Get list of teams actively competing for current player."""
    auction = AuctionSession.query.filter_by(auction_id=session.get("auction_id", "")).first()
    if not auction:
        return []
    
    passed_teams = json.loads(auction.teams_passed) if auction.teams_passed else []
    selected_team = session.get("selected_team")
    interested = []
    
    increment = get_bid_increment(auction.current_bid)
    required_bid = auction.current_bid + increment
    
    # Check all teams
    for t_name in IPL_TEAMS:
        if t_name in passed_teams:
            continue
            
        is_highest = (t_name == auction.highest_bidder)
        
        # Check constraints (role, squad size, etc)
        if not can_team_join_auction(t_name, player.role):
            if not is_highest and t_name not in passed_teams:
                passed_teams.append(t_name)
            continue
            
        # Check budget constraint
        is_human = (t_name == selected_team)
        max_bid = calculate_maximum_bid(t_name, player, auction.current_bid, is_human=is_human)
        if not is_highest and max_bid < required_bid:
            if t_name not in passed_teams:
                passed_teams.append(t_name)
            continue
            
        # AI decision logic
        if t_name != selected_team and not is_highest:
            active_count = len(json.loads(auction.teams_interested)) if auction.teams_interested else len(IPL_TEAMS)
            interest_score = calculate_interest_score(t_name, player, auction.current_bid, active_teams_count=active_count)
            if not should_team_bid(interest_score):
                if t_name not in passed_teams:
                    passed_teams.append(t_name)
                continue
                
        # If passed checks, team is active
        interested.append((t_name, 100))
    
    # Update passed teams
    auction.teams_passed = json.dumps(passed_teams)
    auction.teams_interested = json.dumps(interested)
    db.session.commit()
    
    return interested


def handle_auctioneer_countdown():
    """Handle auctioneer countdown: GOING_ONCE, GOING_TWICE, FINAL_CALL."""
    auction = AuctionSession.query.filter_by(auction_id=session.get("auction_id", "")).first()
    if not auction:
        return
    
    if not auction.countdown_started:
        auction.countdown_started = datetime.utcnow()
        auction.auction_state = "GOING_ONCE"
        db.session.commit()
        log_event("GOING_ONCE")
        return
    
    elapsed = (datetime.utcnow() - auction.countdown_started).total_seconds()
    
    if elapsed < COUNTDOWN_DURATION:
        # Still in GOING_ONCE
        pass
    elif elapsed < COUNTDOWN_DURATION * 2:
        if auction.auction_state != "GOING_TWICE":
            auction.auction_state = "GOING_TWICE"
            db.session.commit()
            log_event("GOING_TWICE")
    elif elapsed < COUNTDOWN_DURATION * 3:
        if auction.auction_state != "FINAL_CALL":
            auction.auction_state = "FINAL_CALL"
            db.session.commit()
            log_event("FINAL_CALL")
    else:
        # Finalize sale or unsold
        finalize_player_status()


def process_auction_events():
    """Event-driven auction progress over time."""
    auction_id = session.get("auction_id", "")
    if not auction_id:
        return
        
    auction = AuctionSession.query.filter_by(auction_id=auction_id).first()
    if not auction or auction.auction_state in ["SOLD", "UNSOLD", "PAUSED"]:
        return

    now = datetime.utcnow()
    player = get_current_player()
    if not player:
        return

    if auction.auction_state == "OPEN":
        import hashlib
        seed_str = str(auction.last_bid_timestamp) + str(auction.current_bid)
        delay_sec = 1.0 + (int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % 250) / 100.0
        
        # Accelerated round is faster
        if auction.auction_stage == "ACCELERATED_ROUND":
            delay_sec = 0.5
            
        # Check if dynamic randomized delay has passed since last bid
        if (now - auction.last_bid_timestamp).total_seconds() >= delay_sec:
            # Attempt AI bid
            interested_teams = get_interested_teams(player)
            selected_team = session.get("selected_team")
            
            valid_ai_teams = []
            
            print(f"\n--- AI EVALUATION | Player: {player.name} ({player.rating}) | Current Bid: ₹{auction.current_bid} Cr ---")
            
            for t, score in interested_teams:
                if t == selected_team or t == auction.highest_bidder:
                    continue
                
                max_bid = calculate_maximum_bid(t, player, auction.current_bid, is_human=False)
                increment = get_bid_increment(auction.current_bid)
                
                active_count = len(interested_teams)
                interest_score = calculate_interest_score(t, player, auction.current_bid, active_teams_count=active_count)
                
                if auction.current_bid + increment <= max_bid:
                    valid_ai_teams.append(t)
                    print(f"{t}: Interest = {int(interest_score)} | Max Bid = {max_bid:.2f} Cr | Decision = BID")
                else:
                    print(f"{t}: Interest = {int(interest_score)} | Max Bid = {max_bid:.2f} Cr | Decision = PASS (Max bid reached)")
            
            if valid_ai_teams:
                # Place AI bid
                import random
                bidding_team = random.choice(valid_ai_teams)
                increment = get_bid_increment(auction.current_bid)
                auction.current_bid = round(auction.current_bid + increment, 2)
                auction.highest_bidder = bidding_team
                auction.last_bid_timestamp = now
                db.session.commit()
                log_event("BID", {"team_name": bidding_team, "amount": auction.current_bid})
            else:
                # No AI wants to bid. Start countdown.
                auction.auction_state = "GOING_ONCE"
                auction.countdown_started = now
                db.session.commit()
                log_event("GOING_ONCE")
                
    elif auction.auction_state in ["GOING_ONCE", "GOING_TWICE", "FINAL_CALL"]:
        handle_auctioneer_countdown()


def finalize_player_status():
    """Finalize whether player is sold or unsold."""
    auction = AuctionSession.query.filter_by(auction_id=session.get("auction_id", "")).first()
    player = get_current_player()
    
    if not auction or not player:
        return
    
    if auction.highest_bidder:
        # Player is sold
        winning_team = Team.query.filter_by(team_name=auction.highest_bidder).first()
        
        if winning_team:
            player.status = "sold"
            player.sold_price = auction.current_bid
            player.sold_to = auction.highest_bidder
            winning_team.budget -= auction.current_bid
            
            db.session.add(player)
            db.session.add(winning_team)
            db.session.add(
                AuctionResult(
                    player_name=player.name,
                    team_name=auction.highest_bidder,
                    sold_price=auction.current_bid,
                )
            )
            db.session.add(
                TeamSquad(
                    team_name=auction.highest_bidder,
                    player_name=player.name,
                    role=player.role,
                    purchase_price=auction.current_bid,
                )
            )
            db.session.commit()
            
            log_event("SOLD", {"team_name": auction.highest_bidder, "amount": auction.current_bid})
    else:
        # Player is unsold
        player.status = "unsold"
        db.session.add(player)
        db.session.commit()
        log_event("UNSOLD", {"player_name": player.name})
    
    auction.auction_state = "SOLD" if auction.highest_bidder else "UNSOLD"
    db.session.commit()


@auction_bp_v2.route("/auction/v2")
def auction():
    selected_team = session.get("selected_team", "").strip().upper()
    if not selected_team or selected_team not in IPL_TEAMS:
        flash("Please select a team before joining the auction.", "warning")
        return redirect(url_for("team_bp.select_team"))
    
    # Initialize if needed
    if not session.get("auction_id"):
        initialize_auction_session()
    
    auction_id = session.get("auction_id", "")
    auction = AuctionSession.query.filter_by(auction_id=auction_id).first()
    
    if not auction:
        session.pop("auction_id", None)
        initialize_auction_session()
        auction_id = session.get("auction_id", "")
        auction = AuctionSession.query.filter_by(auction_id=auction_id).first()
        if not auction:
            flash("No players available for auction.", "warning")
            return redirect(url_for("team_bp.select_team"))
    
    # Check if auction is finished
    if session.get("auction_finished"):
        teams = Team.query.order_by(Team.budget.asc()).all()
        squads = {t.team_name: TeamSquad.query.filter_by(team_name=t.team_name).all() for t in teams}
        return render_template("auction_complete.html", selected_team=selected_team, teams=teams, squads=squads)
    
    player = get_current_player()
    if not player:
        session["auction_finished"] = True
        teams = Team.query.order_by(Team.budget.asc()).all()
        squads = {t.team_name: TeamSquad.query.filter_by(team_name=t.team_name).all() for t in teams}
        return render_template("auction_complete.html", selected_team=selected_team, teams=teams, squads=squads)
    
    # Check if we need to handle countdown
    if auction.auction_state in ["GOING_ONCE", "GOING_TWICE", "FINAL_CALL"]:
        handle_auctioneer_countdown()
        auction = AuctionSession.query.filter_by(auction_id=auction_id).first()
        
        if auction.auction_state in ["SOLD", "UNSOLD"]:
            advance_to_next_player()
            auction.auction_state = "OPEN"
            auction.countdown_started = None
            db.session.commit()
    
    # Get interested teams
    interested_teams = get_interested_teams(player)
    
    # Get team info
    team = Team.query.filter_by(team_name=selected_team).first()
    squad = TeamSquad.query.filter_by(team_name=selected_team).all()
    teams = Team.query.order_by(Team.team_name).all()
    event_log = session.get("event_log", [])
    
    # Calculate squad info
    squad_composition = get_team_squad_composition(selected_team)
    squad_size = len(squad)
    
    from services.auction_set_manager import get_auction_set_name
    set_name = get_auction_set_name(player)
    
    return render_template(
        "auction_v2.html",
        selected_team=selected_team,
        player=player,
        current_bid=auction.current_bid,
        highest_bidder=auction.highest_bidder,
        auction_state=auction.auction_state,
        auction_stage=auction.auction_stage,
        set_name=set_name,
        team=team,
        squad_size=squad_size,
        squad_composition=squad_composition,
        teams=teams,
        event_log=event_log,
        interested_teams=[t for t, _ in interested_teams],
        max_bid_allowed=calculate_maximum_bid(selected_team, player, auction.current_bid, is_human=True),
        max_squad=MAX_SQUAD_SIZE,
        min_squad=MIN_SQUAD_SIZE,
    )


@auction_bp_v2.route("/bid/v2", methods=["POST"])
def bid():
    selected_team = session.get("selected_team")
    auction_id = session.get("auction_id", "")
    
    auction = AuctionSession.query.filter_by(auction_id=auction_id).first()
    player = get_current_player()
    
    if not auction or not player or not selected_team:
        return jsonify({"error": "Invalid auction state"}), 400
        
    if auction.auction_state == "PAUSED":
        flash("Auction is paused by admin.", "warning")
        return redirect(url_for("auction_bp_v2.auction"))
        
    if auction.highest_bidder == selected_team:
        flash("You are already the highest bidder.", "warning")
        return redirect(url_for("auction_bp_v2.auction"))
        
    team_squad_count = TeamSquad.query.filter_by(team_name=selected_team).count()
    if team_squad_count >= 15:
        flash("Your squad is full (Max 15 players allowed).", "danger")
        return redirect(url_for("auction_bp_v2.auction"))
    
    # Check constraints
    max_bid = calculate_maximum_bid(selected_team, player, auction.current_bid, is_human=True)
    increment = get_bid_increment(auction.current_bid)
    next_bid = round(auction.current_bid + increment, 2)
    
    if next_bid > max_bid:
        flash("You cannot bid beyond your maximum allowed bid for this player.", "warning")
        return redirect(url_for("auction_bp_v2.auction"))
    
    team = Team.query.filter_by(team_name=selected_team).first()
    if not team or next_bid > team.budget:
        flash("Insufficient budget to raise the bid.", "danger")
        return redirect(url_for("auction_bp_v2.auction"))
    
    # Place bid
    auction.current_bid = next_bid
    auction.highest_bidder = selected_team
    auction.last_bid_timestamp = datetime.utcnow()
    auction.auction_state = "OPEN"
    auction.countdown_started = None
    db.session.commit()
    
    log_event("BID", {"team_name": selected_team, "amount": next_bid})
    
    return redirect(url_for("auction_bp_v2.auction"))


@auction_bp_v2.route("/pass/v2", methods=["POST"])
def pass_bid():
    """Human player passes on current player."""
    selected_team = session.get("selected_team")
    auction_id = session.get("auction_id", "")
    
    auction = AuctionSession.query.filter_by(auction_id=auction_id).first()
    player = get_current_player()
    
    if not auction or not player or not selected_team:
        return jsonify({"error": "Invalid auction state"}), 400
        
    if auction.auction_state == "PAUSED":
        flash("Auction is paused by admin.", "warning")
        return redirect(url_for("auction_bp_v2.auction"))
    
    # Mark team as passed
    passed_teams = json.loads(auction.teams_passed) if auction.teams_passed else []
    if selected_team not in passed_teams:
        passed_teams.append(selected_team)
    
    auction.teams_passed = json.dumps(passed_teams)
    db.session.commit()
    
    log_event("PASS", {"team_name": selected_team})
    
    # If all teams passed, mark as unsold
    interested_teams = get_interested_teams(player)
    if not interested_teams:
        finalize_player_status()
    elif len(interested_teams) == 1 and interested_teams[0][0] == auction.highest_bidder:
        # Start countdown
        auction.auction_state = "GOING_ONCE"
        auction.countdown_started = datetime.utcnow()
        db.session.commit()
    else:
        auction.auction_state = "OPEN"
        db.session.commit()
    
    return redirect(url_for("auction_bp_v2.auction"))


@auction_bp_v2.route("/squad/v2")
def squad():
    selected_team = session.get("selected_team")
    if not selected_team:
        flash("Please select your team first.", "warning")
        return redirect(url_for("team_bp.select_team"))
    
    squad = TeamSquad.query.filter_by(team_name=selected_team).all()
    team = Team.query.filter_by(team_name=selected_team).first()
    squad_composition = get_team_squad_composition(selected_team)
    
    return render_template(
        "squad.html",
        selected_team=selected_team,
        squad=squad,
        team=team,
        squad_composition=squad_composition,
        min_squad=MIN_SQUAD_SIZE,
        max_squad=MAX_SQUAD_SIZE,
    )


@auction_bp_v2.route("/auction/state", methods=["GET"])
def get_auction_state():
    """API endpoint for frontend polling."""
    # Process any pending events first
    process_auction_events()
    
    auction_id = session.get("auction_id", "")
    auction = AuctionSession.query.filter_by(auction_id=auction_id).first()
    player = get_current_player()
    selected_team = session.get("selected_team")
    
    if not auction or not player:
        return jsonify({"error": "No active auction"}), 400
        
    # Check if we should automatically advance to next player after SOLD/UNSOLD
    if auction.auction_state in ["SOLD", "UNSOLD"]:
        now = datetime.utcnow()
        # Give a 3 second pause after sold/unsold before advancing
        if auction.countdown_started and (now - auction.countdown_started).total_seconds() > COUNTDOWN_DURATION * 3 + 3:
            advance_to_next_player()
            auction = AuctionSession.query.filter_by(auction_id=session.get("auction_id", "")).first()
            player = get_current_player()
            if not auction or not player:
                return jsonify({"status": "finished"})
    
    team = Team.query.filter_by(team_name=selected_team).first()
    event_log = session.get("event_log", [])[:20]
    
    interested_teams = get_interested_teams(player)
    interested_list = [t for t, _ in interested_teams]
    
    return jsonify({
        "player_name": player.name,
        "player_rating": player.rating,
        "current_bid": auction.current_bid,
        "highest_bidder": auction.highest_bidder,
        "auction_state": auction.auction_state,
        "remaining_budget": team.budget if team else 0,
        "countdown_elapsed": (datetime.utcnow() - auction.countdown_started).total_seconds() if auction.countdown_started else 0,
        "recent_events": event_log,
        "interested_teams": interested_list
    })

@auction_bp_v2.route("/auction/pause", methods=["POST"])
def pause_auction():
    auction = AuctionSession.query.filter_by(auction_id=session.get("auction_id", "")).first()
    if auction:
        auction.auction_state = "PAUSED"
        auction.countdown_started = None
        db.session.commit()
        log_event("SYSTEM", {"details": "Auction Paused By Admin"})
    return redirect(url_for("auction_bp_v2.auction"))

@auction_bp_v2.route("/auction/resume", methods=["POST"])
def resume_auction():
    auction = AuctionSession.query.filter_by(auction_id=session.get("auction_id", "")).first()
    if auction and auction.auction_state == "PAUSED":
        auction.auction_state = "OPEN"
        auction.last_bid_timestamp = datetime.utcnow()
        db.session.commit()
        log_event("SYSTEM", {"details": "Auction Resumed By Admin"})
    return redirect(url_for("auction_bp_v2.auction"))

@auction_bp_v2.route("/auction/end", methods=["POST"])
def end_auction():
    auction = AuctionSession.query.filter_by(auction_id=session.get("auction_id", "")).first()
    if auction:
        auction.auction_stage = "COMPLETED"
        db.session.commit()
    session["auction_finished"] = True
    return redirect(url_for("auction_bp_v2.auction"))

@auction_bp_v2.route("/auction/start_new", methods=["POST"])
def start_new_auction():
    TeamSquad.query.delete()
    for team in Team.query.all():
        team.budget = 120.0
    for player in Player.query.all():
        player.status = "available"
        player.sold_price = 0
        player.sold_to = None
    db.session.commit()
    
    session.pop("auction_id", None)
    session.pop("auction_finished", None)
    initialize_auction_session()
    return redirect(url_for("auction_bp_v2.auction"))

@auction_bp_v2.route("/auction/reset", methods=["POST"])
def reset_auction():
    auction_id = session.get("auction_id", "")
    if auction_id:
        TeamSquad.query.delete()
        for team in Team.query.all():
            team.budget = 120.0
        for player in Player.query.all():
            player.status = "available"
            player.sold_price = 0
            player.sold_to = None
            
        auction = AuctionSession.query.filter_by(auction_id=auction_id).first()
        if auction:
            auction.auction_stage = "ROUND_1"
            auction.auction_state = "OPEN"
            auction.highest_bidder = None
            first_player = Player.query.filter_by(status="available").order_by(Player.rating.desc(), Player.base_price.desc()).first()
            if first_player:
                auction.current_player_id = first_player.id
                auction.current_bid = first_player.base_price
            auction.countdown_started = None
            auction.teams_passed = ""
            auction.teams_interested = ""
            
            player_ids = [p.id for p in Player.query.filter_by(status="available").order_by(Player.rating.desc(), Player.base_price.desc()).all()]
            session["auction_player_ids"] = player_ids
            session["current_index"] = 0
            
        db.session.commit()
        session.pop("auction_finished", None)
        flash("Current auction has been reset. Historical logs are preserved.", "success")
    return redirect(url_for("auction_bp_v2.auction"))

