import math
import random
from services.playing_xi_generator import generate_playing_xi
from services.team_analyzer import get_team_spending_analytics
from models.team import Team

def calculate_power_scores():
    teams = Team.query.all()
    spending = get_team_spending_analytics()
    spending_dict = {t["team_name"]: t for t in spending}
    
    scores = []
    for t in teams:
        xi_data = generate_playing_xi(t.team_name)
        strength = xi_data["strength"]
        
        xi_rating = strength.get("avg_rating", 0)
        balance = strength.get("balance_score", 0)
        role_cov = 100 if xi_data["is_complete"] else (len(xi_data.get("xi", [])) / 11) * 100
        
        squad_size = spending_dict.get(t.team_name, {}).get("players_purchased", 0)
        bench_strength = min(100, (squad_size / 25.0) * 100) # Simple bench depth metric
        
        budget_rem = spending_dict.get(t.team_name, {}).get("remaining_budget", 0)
        budget_eff = (budget_rem / 120.0) * 100
        
        power = (xi_rating * 0.50) + (bench_strength * 0.15) + (balance * 0.20) + (role_cov * 0.10) + (budget_eff * 0.05)
        
        scores.append({
            "team_name": t.team_name,
            "power_score": power,
            "batting": strength.get("batting_strength", 0),
            "bowling": strength.get("bowling_strength", 0),
            "balance": balance
        })
    return sorted(scores, key=lambda x: x["power_score"], reverse=True)

def _softmax(scores_list, temperature=8.0):
    if not scores_list: return []
    max_score = max(scores_list)
    exp_scores = [math.exp((s - max_score) / temperature) for s in scores_list]
    sum_exp = sum(exp_scores)
    return [e / sum_exp for e in exp_scores]

def get_confidence_rating(prob):
    pct = prob * 100
    if pct > 35: return "High"
    if pct >= 20: return "Medium"
    return "Low"

def calculate_probabilities():
    power_scores = calculate_power_scores()
    if not power_scores:
        return []
        
    scores_only = [p["power_score"] for p in power_scores]
    probs = _softmax(scores_only, temperature=8.0)
    
    results = []
    for i, p in enumerate(power_scores):
        prob = probs[i]
        playoff_prob = min(1.0, prob * 3.5) # Rough heuristic for top 4
        runner_up = prob * 0.5
        
        results.append({
            "team_name": p["team_name"],
            "power_score": p["power_score"],
            "champion_prob": prob,
            "runner_up_prob": runner_up,
            "playoff_prob": playoff_prob,
            "confidence": get_confidence_rating(prob)
        })
    return sorted(results, key=lambda x: x["champion_prob"], reverse=True)

def project_league_table():
    probs = calculate_probabilities()
    results = []
    for i, p in enumerate(probs):
        # Weighted share of wins. A normal team wins ~7 games out of 14.
        # Prob * 70 total wins.
        expected_wins = p["champion_prob"] * 70
        expected_wins = max(3.0, expected_wins) # Cap floor
        expected_wins = min(11.0, expected_wins) # Cap ceiling
        
        results.append({
            "team_name": p["team_name"],
            "power_score": p["power_score"],
            "expected_wins": expected_wins,
            "expected_points": expected_wins * 2
        })
    
    results.sort(key=lambda x: x["expected_points"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results

def run_season_simulation(iterations, volatility):
    volatility_map = {"Low": 6.0, "Medium": 8.0, "High": 13.0}
    temp = volatility_map.get(volatility, 8.0)
    
    power_scores = calculate_power_scores()
    if not power_scores:
        return []
        
    names = [p["team_name"] for p in power_scores]
    scores = [p["power_score"] for p in power_scores]
    
    champion_counts = {name: 0 for name in names}
    probs = _softmax(scores, temperature=temp)
    
    if iterations > 0:
        champs = random.choices(names, weights=probs, k=iterations)
        for c in champs:
            champion_counts[c] += 1
            
    sorted_results = [{"team_name": k, "wins": v, "percentage": (v/iterations)*100 if iterations > 0 else 0} for k, v in champion_counts.items()]
    sorted_results.sort(key=lambda x: x["wins"], reverse=True)
    return sorted_results

def predict_matchup(team_a, team_b):
    scores = calculate_power_scores()
    data_a = next((s for s in scores if s["team_name"] == team_a), None)
    data_b = next((s for s in scores if s["team_name"] == team_b), None)
    
    if not data_a or not data_b:
        return {"a_name": team_a, "b_name": team_b, "a_prob": 50, "b_prob": 50}
        
    score_a = data_a["power_score"] + data_a["batting"] + data_a["bowling"] + data_a["balance"]
    score_b = data_b["power_score"] + data_b["batting"] + data_b["bowling"] + data_b["balance"]
    
    probs = _softmax([score_a, score_b], temperature=12.0) # Higher temp for single game variance
    return {
        "a_name": team_a,
        "b_name": team_b,
        "a_prob": probs[0] * 100,
        "b_prob": probs[1] * 100
    }

def generate_insights():
    scores = calculate_power_scores()
    if not scores: return []
    
    insights = []
    
    strongest_bowl = max(scores, key=lambda x: x["bowling"])
    insights.append(f"{strongest_bowl['team_name']} has the strongest bowling attack.")
    
    strongest_bat = max(scores, key=lambda x: x["batting"])
    insights.append(f"{strongest_bat['team_name']} has the most explosive batting lineup.")
    
    best_balance = max(scores, key=lambda x: x["balance"])
    insights.append(f"{best_balance['team_name']} has the most balanced squad.")
    
    worst_balance = min(scores, key=lambda x: x["balance"])
    insights.append(f"{worst_balance['team_name']} lacks critical role depth.")
    
    return insights
