import random
from models.player import Player
from models.team import Team
from models.squad import TeamSquad

TEAM_PERSONALITIES = {
    "CSK": {"rating_weight": 0.30, "role_weight": 0.40, "budget_weight": 0.20, "balance_weight": 0.10},
    "MI": {"rating_weight": 0.50, "role_weight": 0.20, "budget_weight": 0.20, "balance_weight": 0.10},
    "RCB": {"rating_weight": 0.60, "role_weight": 0.15, "budget_weight": 0.15, "balance_weight": 0.10},
    "KKR": {"rating_weight": 0.40, "role_weight": 0.30, "budget_weight": 0.20, "balance_weight": 0.10},
    "SRH": {"rating_weight": 0.35, "role_weight": 0.35, "budget_weight": 0.20, "balance_weight": 0.10},
    "DC": {"rating_weight": 0.45, "role_weight": 0.25, "budget_weight": 0.20, "balance_weight": 0.10},
    "GT": {"rating_weight": 0.40, "role_weight": 0.30, "budget_weight": 0.20, "balance_weight": 0.10},
    "PBKS": {"rating_weight": 0.50, "role_weight": 0.20, "budget_weight": 0.20, "balance_weight": 0.10},
    "RR": {"rating_weight": 0.35, "role_weight": 0.30, "budget_weight": 0.25, "balance_weight": 0.10},
    "LSG": {"rating_weight": 0.40, "role_weight": 0.30, "budget_weight": 0.20, "balance_weight": 0.10},
}

TARGET_SQUAD_COMPOSITION = {
    "Batter": {"min": 6, "max": 8},
    "Bowler": {"min": 5, "max": 7},
    "All-Rounder": {"min": 3, "max": 5},
    "Wicket Keeper": {"min": 1, "max": 3},
}

ROLE_ALIASES = {
    "Batsman": "Batter",
    "Batter": "Batter",
    "Bowler": "Bowler",
    "All-Rounder": "All-Rounder",
    "Wicket Keeper": "Wicket Keeper",
}


def normalize_role(role):
    for key, normalized in ROLE_ALIASES.items():
        if key.lower() in role.lower():
            return normalized
    return "All-Rounder"


def get_rating_score(rating):
    if rating >= 95:
        return 100
    if rating >= 90:
        return 90
    if rating >= 80:
        return 75
    if rating >= 70:
        return 60
    return 40


def get_role_need_score(team_name, player_role):
    squad = TeamSquad.query.filter_by(team_name=team_name).all()
    role_counts = {}
    for member in squad:
        normalized_role = normalize_role(member.role)
        role_counts[normalized_role] = role_counts.get(normalized_role, 0) + 1

    normalized_player_role = normalize_role(player_role)
    current_count = role_counts.get(normalized_player_role, 0)
    target_min = TARGET_SQUAD_COMPOSITION.get(normalized_player_role, {}).get("min", 2)
    target_max = TARGET_SQUAD_COMPOSITION.get(normalized_player_role, {}).get("max", 5)

    if current_count < target_min:
        return 100
    if current_count <= target_max:
        return 70
    return 40


def get_budget_score(remaining_budget):
    if remaining_budget >= 100:
        return 100
    if remaining_budget >= 60:
        return 70
    if remaining_budget >= 20:
        return 30
    return 10


def get_squad_balance_score(team_name, player_role):
    squad = TeamSquad.query.filter_by(team_name=team_name).all()
    role_counts = {}
    for member in squad:
        normalized_role = normalize_role(member.role)
        role_counts[normalized_role] = role_counts.get(normalized_role, 0) + 1

    normalized_player_role = normalize_role(player_role)
    current_count = role_counts.get(normalized_player_role, 0)
    target_min = TARGET_SQUAD_COMPOSITION.get(normalized_player_role, {}).get("min", 2)
    target_max = TARGET_SQUAD_COMPOSITION.get(normalized_player_role, {}).get("max", 5)

    if current_count < target_min:
        return 100
    if current_count == target_max:
        return 50
    if current_count > target_max:
        return 20
    return 70


def get_randomness_score():
    return random.randint(0, 100)


def calculate_interest_score(team_name, player):
    personality = TEAM_PERSONALITIES.get(team_name, TEAM_PERSONALITIES["CSK"])
    team = Team.query.filter_by(team_name=team_name).first()
    if not team:
        return 0

    rating_score = get_rating_score(player.rating)
    role_need_score = get_role_need_score(team_name, player.role)
    budget_score = get_budget_score(team.budget)
    balance_score = get_squad_balance_score(team_name, player.role)
    randomness_score = get_randomness_score()

    weighted_score = (
        (rating_score * personality["rating_weight"] / 0.40) +
        (role_need_score * personality["role_weight"] / 0.25) +
        (budget_score * personality["budget_weight"] / 0.20) +
        (balance_score * personality["balance_weight"] / 0.10) +
        (randomness_score * 0.05)
    )

    interest_score = min(weighted_score, 100)
    return interest_score


def should_ai_bid(interest_score):
    if interest_score >= 80:
        return random.random() < 0.90
    if interest_score >= 60:
        return random.random() < 0.60
    return random.random() < 0.20


def get_bid_increment(bid_value):
    if bid_value < 1:
        return 0.1
    if bid_value < 2:
        return 0.2
    if bid_value < 10:
        return 1.0
    return 2.0
