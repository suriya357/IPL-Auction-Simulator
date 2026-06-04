from models.player import Player
from models.team import Team
from models.squad import TeamSquad
from models.ai_engine_v2 import SQUAD_TARGETS, normalize_role

def get_auction_overview():
    sold_players = Player.query.filter_by(status="sold").all()
    unsold_players = Player.query.filter_by(status="unsold").all()
    
    total_spend = sum(p.sold_price for p in sold_players) if sold_players else 0
    avg_price = total_spend / len(sold_players) if sold_players else 0
    
    most_expensive = max(sold_players, key=lambda p: p.sold_price) if sold_players else None
    cheapest = min(sold_players, key=lambda p: p.sold_price) if sold_players else None
    highest_rated = max(sold_players, key=lambda p: p.rating) if sold_players else None
    
    avg_squad_rating = sum(p.rating for p in sold_players) / len(sold_players) if sold_players else 0
    
    return {
        "total_sold": len(sold_players),
        "total_unsold": len(unsold_players),
        "total_spend": total_spend,
        "avg_sale_price": avg_price,
        "most_expensive": most_expensive,
        "cheapest": cheapest,
        "highest_rated": highest_rated,
        "avg_squad_rating": avg_squad_rating
    }

def get_team_spending_analytics():
    teams = Team.query.all()
    analytics = []
    
    for t in teams:
        squad = TeamSquad.query.filter_by(team_name=t.team_name).all()
        players_purchased = len(squad)
        total_spend = 120.0 - t.budget
        
        # Calculate average rating
        player_names = [p.player_name for p in squad]
        if player_names:
            players_data = Player.query.filter(Player.name.in_(player_names)).all()
            avg_rating = sum(p.rating for p in players_data) / len(players_data)
        else:
            avg_rating = 0
            
        utilization = (total_spend / 120.0) * 100
        
        analytics.append({
            "team_name": t.team_name,
            "players_purchased": players_purchased,
            "total_spend": total_spend,
            "remaining_budget": t.budget,
            "avg_rating": avg_rating,
            "utilization": utilization
        })
        
    # Sort by total spend desc
    analytics.sort(key=lambda x: x["total_spend"], reverse=True)
    return analytics

def get_top_value_purchases(limit=10):
    sold_players = Player.query.filter_by(status="sold").all()
    values = []
    
    for p in sold_players:
        if p.sold_price and p.sold_price > 0:
            value_score = p.rating / p.sold_price
            values.append({
                "player": p.name,
                "team": p.sold_to,
                "rating": p.rating,
                "price": p.sold_price,
                "value_score": value_score
            })
            
    values.sort(key=lambda x: x["value_score"], reverse=True)
    return values[:limit]

def get_most_expensive_purchases(limit=10):
    sold_players = Player.query.filter_by(status="sold").order_by(Player.sold_price.desc()).limit(limit).all()
    purchases = []
    for p in sold_players:
        purchases.append({
            "player": p.name,
            "team": p.sold_to,
            "price": p.sold_price,
            "rating": p.rating
        })
    return purchases

def get_role_distribution():
    teams = Team.query.all()
    dist = {}
    
    for t in teams:
        squad = TeamSquad.query.filter_by(team_name=t.team_name).all()
        team_dist = {role: {"count": 0, "target": SQUAD_TARGETS[role]["min"], "status": "Red"} for role in SQUAD_TARGETS.keys()}
        
        for player in squad:
            role = normalize_role(player.role)
            if role in team_dist:
                team_dist[role]["count"] += 1
                
        for role in team_dist:
            count = team_dist[role]["count"]
            target = team_dist[role]["target"]
            if count >= target:
                team_dist[role]["status"] = "Green"
            elif count > 0:
                team_dist[role]["status"] = "Yellow"
                
        dist[t.team_name] = team_dist
    return dist

def get_team_strength_preview():
    teams = Team.query.all()
    strengths = []
    dist = get_role_distribution()
    
    for t in teams:
        squad = TeamSquad.query.filter_by(team_name=t.team_name).all()
        
        # Avg Rating
        player_names = [p.player_name for p in squad]
        if player_names:
            players_data = Player.query.filter(Player.name.in_(player_names)).all()
            avg_rating = sum(p.rating for p in players_data) / len(players_data)
        else:
            avg_rating = 0
            
        # Squad Balance
        balance_score = 100
        team_dist = dist.get(t.team_name, {})
        for role_data in team_dist.values():
            if role_data["count"] < role_data["target"]:
                balance_score -= 25 # Penalty for missing target
                
        balance_score = max(0, balance_score)
        
        # Budget %
        budget_pct = (t.budget / 120.0) * 100
        
        strength_score = (avg_rating * 0.6) + (balance_score * 0.3) + (budget_pct * 0.1)
        
        strengths.append({
            "team_name": t.team_name,
            "strength_score": strength_score,
            "avg_rating": avg_rating,
            "balance_score": balance_score,
            "budget_pct": budget_pct
        })
        
    strengths.sort(key=lambda x: x["strength_score"], reverse=True)
    return strengths

def get_advanced_efficiency_metrics():
    # Helper to calculate advanced metrics
    teams_analytics = get_team_spending_analytics()
    value_purchases = get_top_value_purchases(limit=100)
    
    # Best Value Team
    team_values = {}
    for v in value_purchases:
        team = v["team"]
        if team not in team_values:
            team_values[team] = []
        team_values[team].append(v["value_score"])
        
    best_value_team = None
    best_value_avg = 0
    for t, scores in team_values.items():
        avg = sum(scores) / len(scores)
        if avg > best_value_avg:
            best_value_avg = avg
            best_value_team = t
            
    most_efficient_purchase = value_purchases[0] if value_purchases else None
    most_aggressive_buyer = max(teams_analytics, key=lambda x: x["utilization"]) if teams_analytics else None
    highest_avg_rating = max(teams_analytics, key=lambda x: x["avg_rating"]) if teams_analytics else None
    
    # Lowest Cost Per Rating Point
    lowest_cost_team = None
    lowest_cost_val = float('inf')
    
    for t in teams_analytics:
        # Total rating points = avg_rating * players
        total_rating = t["avg_rating"] * t["players_purchased"]
        if total_rating > 0:
            cost_per_point = t["total_spend"] / total_rating
            if cost_per_point < lowest_cost_val:
                lowest_cost_val = cost_per_point
                lowest_cost_team = t["team_name"]
                
    return {
        "best_value_team": best_value_team,
        "best_value_avg": best_value_avg,
        "most_efficient_purchase": most_efficient_purchase,
        "most_aggressive_buyer": most_aggressive_buyer["team_name"] if most_aggressive_buyer else None,
        "highest_avg_rating_squad": highest_avg_rating["team_name"] if highest_avg_rating else None,
        "lowest_cost_per_rating_team": lowest_cost_team,
        "lowest_cost_per_rating_val": lowest_cost_val if lowest_cost_val != float('inf') else 0
    }
