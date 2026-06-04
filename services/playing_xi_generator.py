from models.player import Player
from models.team import Team
from models.squad import TeamSquad
from models.ai_engine_v2 import normalize_role

def generate_playing_xi(team_name):
    squad = TeamSquad.query.filter_by(team_name=team_name).all()
    if not squad:
        return {"is_complete": False, "message": "Squad is empty.", "xi": [], "strength": {}}
        
    player_names = [p.player_name for p in squad]
    players_data = Player.query.filter(Player.name.in_(player_names)).all()
    
    # Enrich and sort all players by rating desc
    enriched = []
    for s in squad:
        p_data = next((p for p in players_data if p.name == s.player_name), None)
        if p_data:
            enriched.append({
                "name": p_data.name,
                "role": normalize_role(p_data.role),
                "rating": p_data.rating,
                "price": s.purchase_price,
                "value_score": (p_data.rating / s.purchase_price) if s.purchase_price > 0 else 0
            })
            
    enriched.sort(key=lambda x: x["rating"], reverse=True)
    
    # Categorize
    wk = [p for p in enriched if p["role"] == "Wicket Keeper"]
    batters = [p for p in enriched if p["role"] == "Batter"]
    bowlers = [p for p in enriched if p["role"] == "Bowler"]
    ar = [p for p in enriched if p["role"] == "All-Rounder"]
    
    selected_xi = []
    
    # Mandatory pulls
    if wk:
        selected_xi.append(wk.pop(0))
    if ar:
        selected_xi.append(ar.pop(0))
        
    for _ in range(min(3, len(batters))):
        selected_xi.append(batters.pop(0))
        
    for _ in range(min(3, len(bowlers))):
        selected_xi.append(bowlers.pop(0))
        
    # Fill remaining from the pool of unused
    remaining_pool = wk + batters + bowlers + ar
    remaining_pool.sort(key=lambda x: x["rating"], reverse=True)
    
    slots_needed = 11 - len(selected_xi)
    for _ in range(min(slots_needed, len(remaining_pool))):
        selected_xi.append(remaining_pool.pop(0))
        
    is_complete = len(selected_xi) == 11
    
    # Calculate Strengths
    avg_rating = sum(p["rating"] for p in selected_xi) / len(selected_xi) if selected_xi else 0
    
    xi_batters = [p for p in selected_xi if p["role"] in ["Batter", "Wicket Keeper", "All-Rounder"]]
    batting_str = sum(p["rating"] for p in xi_batters) / len(xi_batters) if xi_batters else 0
    
    xi_bowlers = [p for p in selected_xi if p["role"] in ["Bowler", "All-Rounder"]]
    bowling_str = sum(p["rating"] for p in xi_bowlers) / len(xi_bowlers) if xi_bowlers else 0
    
    # Balance score (max 100)
    has_wk = any(p["role"] == "Wicket Keeper" for p in selected_xi)
    bat_count = len([p for p in selected_xi if p["role"] == "Batter"])
    bowl_count = len([p for p in selected_xi if p["role"] == "Bowler"])
    ar_count = len([p for p in selected_xi if p["role"] == "All-Rounder"])
    
    balance_score = 100
    if not has_wk: balance_score -= 20
    if bat_count < 3: balance_score -= (3 - bat_count) * 10
    if bowl_count < 3: balance_score -= (3 - bowl_count) * 10
    if ar_count < 1: balance_score -= 10
    balance_score = max(0, balance_score)
    
    role_coverage = 100 if is_complete else (len(selected_xi) / 11) * 100
    
    overall_strength = (avg_rating * 0.5) + (balance_score * 0.3) + (role_coverage * 0.2)
    
    # Captain & MVP
    captain = max(selected_xi, key=lambda x: x["rating"]) if selected_xi else None
    mvp = max(selected_xi, key=lambda x: x["value_score"]) if selected_xi else None
    most_expensive = max(selected_xi, key=lambda x: x["price"]) if selected_xi else None
    
    strength_data = {
        "avg_rating": avg_rating,
        "batting_strength": batting_str,
        "bowling_strength": bowling_str,
        "balance_score": balance_score,
        "overall_strength": overall_strength
    }
    
    # Sort XI by role for display: WK -> Batters -> AR -> Bowlers
    role_order = {"Wicket Keeper": 0, "Batter": 1, "All-Rounder": 2, "Bowler": 3}
    selected_xi.sort(key=lambda x: (role_order.get(x["role"], 4), -x["rating"]))
    
    return {
        "is_complete": is_complete,
        "message": "" if is_complete else "Squad does not have enough players for an ideal Playing XI.",
        "xi": selected_xi,
        "strength": strength_data,
        "captain": captain,
        "mvp": mvp,
        "most_expensive": most_expensive,
        "team_name": team_name
    }

def get_all_teams_xi_comparison():
    teams = Team.query.all()
    results = []
    for t in teams:
        data = generate_playing_xi(t.team_name)
        if data["xi"]:
            results.append({
                "team_name": t.team_name,
                "overall_strength": data["strength"]["overall_strength"],
                "avg_rating": data["strength"]["avg_rating"],
                "batting_strength": data["strength"]["batting_strength"],
                "bowling_strength": data["strength"]["bowling_strength"],
                "balance_score": data["strength"]["balance_score"],
                "is_complete": data["is_complete"]
            })
            
    results.sort(key=lambda x: x["overall_strength"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results
