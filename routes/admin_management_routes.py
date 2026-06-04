from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from extensions import db
from models.player import Player
from models.team import Team
from models.auction_session import AuctionSession
from services.player_value_engine import get_player_tier, get_expected_price_range
from services.auction_set_manager import get_auction_set_name
import csv
from io import StringIO

admin_mgmt_bp = Blueprint("admin_mgmt_bp", __name__, template_folder="../templates")

@admin_mgmt_bp.route("/admin/auction-overview")
def auction_overview():
    players = Player.query.all()
    
    total = len(players)
    tier_counts = {"Tier 1: Superstar": 0, "Tier 2: Star": 0, "Tier 3: Quality Player": 0, "Tier 4: Squad Player": 0}
    status_counts = {"available": 0, "sold": 0, "unsold": 0, "accelerated": 0}
    set_counts = {}
    
    for p in players:
        if p.tier in tier_counts:
            tier_counts[p.tier] += 1
            
        status = p.status
        if status in status_counts:
            status_counts[status] += 1
        elif p.auction_round == "ACCELERATED_ROUND" and status == "unsold":
            status_counts["accelerated"] += 1
            
        s_name = p.auction_set or "Unknown"
        set_counts[s_name] = set_counts.get(s_name, 0) + 1

    return render_template("admin_overview.html", 
                           total=total, 
                           tier_counts=tier_counts, 
                           status_counts=status_counts,
                           set_counts=set_counts)

@admin_mgmt_bp.route("/admin/player-tiers")
def player_tiers():
    players = Player.query.all()
    # Group by tier
    tiers = {"Tier 1: Superstar": [], "Tier 2: Star": [], "Tier 3: Quality Player": [], "Tier 4: Squad Player": [], "Unassigned": []}
    for p in players:
        if p.tier in tiers:
            tiers[p.tier].append(p)
        else:
            tiers["Unassigned"].append(p)
            
    teams = Team.query.all()
    return render_template("admin_player_tiers.html", tiers=tiers, teams=teams)

@admin_mgmt_bp.route("/admin/auction-sets")
def auction_sets():
    players = Player.query.all()
    # Group by sets
    sets = {}
    for p in players:
        s_name = p.auction_set or "Unassigned"
        if s_name not in sets:
            sets[s_name] = []
        sets[s_name].append(p)
        
    teams = Team.query.all()
    return render_template("admin_auction_sets.html", sets=sets, teams=teams)

@admin_mgmt_bp.route("/admin/player/<int:player_id>")
def player_details(player_id):
    player = Player.query.get_or_404(player_id)
    min_price, max_price = get_expected_price_range(player.rating)
    return render_template("admin_player_details.html", player=player, min_price=min_price, max_price=max_price)

@admin_mgmt_bp.route("/admin/live-monitor")
def live_monitor():
    return render_template("admin_live_monitor.html")

@admin_mgmt_bp.route("/admin/recalculate-tiers", methods=["POST"])
def recalculate_tiers():
    players = Player.query.all()
    count_tier = 0
    count_set = 0
    for p in players:
        if not p.manual_tier_lock:
            p.tier = get_player_tier(p.rating)
            count_tier += 1
        if not p.manual_set_lock:
            p.auction_set = get_auction_set_name(p)
            count_set += 1
            
    db.session.commit()
    flash(f"Recalculated {count_tier} tiers and {count_set} sets. Manual locks were respected.", "success")
    return redirect(request.referrer or url_for('admin_bp.admin'))

@admin_mgmt_bp.route("/admin/players/update-tier", methods=["POST"])
def update_tier():
    data = request.json
    player_id = data.get("player_id")
    new_tier = data.get("tier")
    
    player = Player.query.get(player_id)
    if player:
        player.tier = new_tier
        # Optionally auto-lock when manually moved
        player.manual_tier_lock = True
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 404

@admin_mgmt_bp.route("/admin/players/update-set", methods=["POST"])
def update_set():
    data = request.json
    player_id = data.get("player_id")
    new_set = data.get("set")
    
    player = Player.query.get(player_id)
    if player:
        player.auction_set = new_set
        # Optionally auto-lock
        player.manual_set_lock = True
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 404

@admin_mgmt_bp.route("/admin/players/bulk-action", methods=["POST"])
def bulk_action():
    action = request.form.get("action")
    player_ids = request.form.getlist("player_ids")
    target_tier = request.form.get("target_tier")
    target_set = request.form.get("target_set")
    
    if not player_ids:
        flash("No players selected.", "warning")
        return redirect(request.referrer)
        
    players = Player.query.filter(Player.id.in_(player_ids)).all()
    
    for p in players:
        if action == "move_tier" and target_tier:
            p.tier = target_tier
            p.manual_tier_lock = True
        elif action == "move_set" and target_set:
            p.auction_set = target_set
            p.manual_set_lock = True
        elif action == "lock_tier":
            p.manual_tier_lock = True
        elif action == "unlock_tier":
            p.manual_tier_lock = False
        elif action == "lock_set":
            p.manual_set_lock = True
        elif action == "unlock_set":
            p.manual_set_lock = False
        elif action == "mark_unsold":
            p.status = "unsold"
            p.sold_price = None
            p.sold_to = None
        elif action == "reset_status":
            p.status = "available"
            p.sold_price = None
            p.sold_to = None
            
    db.session.commit()
    flash(f"Bulk action '{action}' applied to {len(players)} players.", "success")
    return redirect(request.referrer)

@admin_mgmt_bp.route("/admin/export/players")
def export_players():
    export_type = request.args.get("type", "all")
    
    query = Player.query
    if export_type == "sold":
        query = query.filter_by(status="sold")
    elif export_type == "unsold":
        query = query.filter_by(status="unsold")
        
    players = query.all()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["ID", "Name", "Role", "Rating", "Base Price", "Tier", "Auction Set", "Status", "Sold Price", "Sold To"])
    
    for p in players:
        cw.writerow([p.id, p.name, p.role, p.rating, p.base_price, p.tier, p.auction_set, p.status, p.sold_price, p.sold_to])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=players_export_{export_type}.csv"
    output.headers["Content-type"] = "text/csv"
    return output
