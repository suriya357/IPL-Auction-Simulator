from models.player import Player
from models.team import Team
from models.squad import TeamSquad
from sqlalchemy import func
import random

# Realistic IPL Squad Targets
SQUAD_TARGETS = {
    "Batter": {"min": 4, "max": 6},
    "Bowler": {"min": 4, "max": 6},
    "All-Rounder": {"min": 2, "max": 4},
    "Wicket Keeper": {"min": 1, "max": 2},
}

MIN_SQUAD_SIZE = 11
MAX_SQUAD_SIZE = 15
MINIMUM_PLAYER_COST = 1.0  # Minimum cost per player

# Team Personalities with unique characteristics
TEAM_PERSONALITIES = {
    "CSK": {
        "name": "Chennai Super Kings",
        "style": "Conservative",
        "aggression": 1.0,
        "rating_preference": 0.30,
        "role_preference": 0.30,
        "budget_preference": 0.25,
        "balance_preference": 0.15,
        "max_spend_single_player": 0.20,
    },
    "MI": {
        "name": "Mumbai Indians",
        "style": "Aggressive for stars",
        "aggression": 1.3,
        "rating_preference": 0.50,
        "role_preference": 0.20,
        "budget_preference": 0.15,
        "balance_preference": 0.15,
        "max_spend_single_player": 0.30,
    },
    "RCB": {
        "name": "Royal Challengers Bangalore",
        "style": "Very aggressive for batters",
        "aggression": 1.4,
        "rating_preference": 0.40,
        "role_preference": 0.40,
        "budget_preference": 0.10,
        "balance_preference": 0.10,
        "max_spend_single_player": 0.35,
    },
    "KKR": {
        "name": "Kolkata Knight Riders",
        "style": "Aggressive",
        "aggression": 1.25,
        "rating_preference": 0.35,
        "role_preference": 0.30,
        "budget_preference": 0.20,
        "balance_preference": 0.15,
        "max_spend_single_player": 0.25,
    },
    "SRH": {
        "name": "Sunrisers Hyderabad",
        "style": "Balanced",
        "aggression": 1.1,
        "rating_preference": 0.35,
        "role_preference": 0.35,
        "budget_preference": 0.15,
        "balance_preference": 0.15,
        "max_spend_single_player": 0.20,
    },
    "DC": {
        "name": "Delhi Capitals",
        "style": "Youth-focused",
        "aggression": 1.05,
        "rating_preference": 0.35,
        "role_preference": 0.35,
        "budget_preference": 0.20,
        "balance_preference": 0.10,
        "max_spend_single_player": 0.20,
    },
    "GT": {
        "name": "Gujarat Titans",
        "style": "Balanced",
        "aggression": 1.1,
        "rating_preference": 0.30,
        "role_preference": 0.30,
        "budget_preference": 0.30,
        "balance_preference": 0.10,
        "max_spend_single_player": 0.20,
    },
    "PBKS": {
        "name": "Punjab Kings",
        "style": "Risk-taking",
        "aggression": 1.35,
        "rating_preference": 0.45,
        "role_preference": 0.25,
        "budget_preference": 0.15,
        "balance_preference": 0.15,
        "max_spend_single_player": 0.28,
    },
    "RR": {
        "name": "Rajasthan Royals",
        "style": "Budget-conscious",
        "aggression": 0.9,
        "rating_preference": 0.35,
        "role_preference": 0.30,
        "budget_preference": 0.20,
        "balance_preference": 0.15,
        "max_spend_single_player": 0.18,
    },
    "LSG": {
        "name": "Lucknow Super Giants",
        "style": "Aggressive",
        "aggression": 1.25,
        "rating_preference": 0.35,
        "role_preference": 0.30,
        "budget_preference": 0.20,
        "balance_preference": 0.15,
        "max_spend_single_player": 0.25,
    },
}


def normalize_role(role):
    """Normalize role names."""
    if not role:
        return "Unknown"
    role = role.strip()
    if role in ["Batsman", "Batter"]:
        return "Batter"
    elif role == "Bowler":
        return "Bowler"
    elif role in ["All-Rounder", "All Rounder"]:
        return "All-Rounder"
    elif role in ["Wicket Keeper", "Wicket-Keeper", "WK"]:
        return "Wicket Keeper"
    return role


def get_team_squad_composition(team_name):
    """Get current squad composition for a team."""
    squad = TeamSquad.query.filter_by(team_name=team_name).all()
    composition = {}
    for role_key in SQUAD_TARGETS.keys():
        composition[role_key] = 0
    
    for player in squad:
        normalized = normalize_role(player.role)
        composition[normalized] = composition.get(normalized, 0) + 1
    
    return composition


def calculate_budget_reservation(team_name, remaining_budget):
    """Calculate budget to reserve for remaining squad slots."""
    squad = TeamSquad.query.filter_by(team_name=team_name).all()
    current_squad_size = len(squad)
    slots_needed = max(0, MIN_SQUAD_SIZE - current_squad_size)
    
    # Reserve at least 1 Cr per slot needed
    reserve = slots_needed * MINIMUM_PLAYER_COST
    available = max(0, remaining_budget - reserve)
    
    return available, reserve


def get_auction_stage(team_name):
    """Determine auction stage based on squad size."""
    squad_size = TeamSquad.query.filter_by(team_name=team_name).count()
    
    if squad_size <= 5:
        return "EARLY", 1.2  # Can spend more aggressively
    elif squad_size <= 10:
        return "MID", 1.0   # Balanced spending
    else:
        return "LATE", 0.7  # Conservative spending


def calculate_rating_score(rating):
    """Convert player rating to score."""
    if rating >= 95:
        return 100
    elif rating >= 90:
        return 90
    elif rating >= 80:
        return 75
    elif rating >= 70:
        return 60
    else:
        return 40


def calculate_role_need_score(team_name, player_role):
    """Calculate how much a team needs a specific role."""
    normalized_role = normalize_role(player_role)
    composition = get_team_squad_composition(team_name)
    current_count = composition.get(normalized_role, 0)
    target_min = SQUAD_TARGETS.get(normalized_role, {}).get("min", 0)
    target_max = SQUAD_TARGETS.get(normalized_role, {}).get("max", 15)
    
    if current_count >= target_max:
        return 0  # Role is already fulfilled
    elif current_count < target_min:
        return 100  # Desperately need this role
    else:
        # Partially fulfilled, need 50 points
        return 50


def calculate_budget_health_score(team_name, remaining_budget):
    """Calculate budget health score."""
    available, _ = calculate_budget_reservation(team_name, remaining_budget)
    
    if available >= 10.0:
        return 100
    elif available >= 5.0:
        return 70
    elif available >= 2.0:
        return 40
    else:
        return 10


def calculate_squad_balance_score(team_name, player_role):
    """Calculate score boost for squad balance."""
    normalized_role = normalize_role(player_role)
    composition = get_team_squad_composition(team_name)
    
    # Count underrepresented roles
    underrepresented = 0
    for role_key, count in composition.items():
        if count < SQUAD_TARGETS.get(role_key, {}).get("min", 0):
            underrepresented += 1
    
    # Boost if this role is underrepresented
    if normalized_role in [r for r, c in composition.items() if c < SQUAD_TARGETS.get(r, {}).get("min", 0)]:
        return 20
    
    return 0


def calculate_interest_score(team_name, player, current_bid, active_teams_count=0):
    """Calculate comprehensive interest score for a team in a player."""
    if team_name not in TEAM_PERSONALITIES:
        return 0
    
    personality = TEAM_PERSONALITIES[team_name]
    
    # Rating score
    rating_score = calculate_rating_score(player.rating)
    
    # Role need score
    role_score = calculate_role_need_score(team_name, player.role)
    
    # Get team and budget info
    team = Team.query.filter_by(team_name=team_name).first()
    if not team:
        return 0
    
    # Budget health score
    budget_score = calculate_budget_health_score(team_name, team.budget)
    
    # Squad balance score
    balance_score = calculate_squad_balance_score(team_name, player.role)
    
    # Combined score using personality weights
    interest = (
        (rating_score * personality["rating_preference"]) +
        (role_score * personality["role_preference"]) +
        (budget_score * personality["budget_preference"]) +
        (balance_score * personality["balance_preference"])
    )
    
    # Team Requirement Multiplier (Role Urgency)
    normalized_role = normalize_role(player.role)
    composition = get_team_squad_composition(team_name)
    current_count = composition.get(normalized_role, 0)
    target_min = SQUAD_TARGETS.get(normalized_role, {}).get("min", 0)
    target_max = SQUAD_TARGETS.get(normalized_role, {}).get("max", 15)

    if current_count < target_min:
        interest *= 1.8  # Desperately need
    elif current_count >= target_max:
        interest *= 0.5  # Already satisfied
        
    # Apply momentum bonus for premium players
    if player.rating >= 85:
        if active_teams_count >= 5:
            interest += 15
        elif active_teams_count >= 3:
            interest += 10
            
    # Random factor (adds slight unpredictability)
    interest += random.randint(0, 100) * 0.05
    
    return min(100, interest)


def should_team_bid(interest_score):
    """Determine if team should bid based on interest score."""
    if interest_score >= 80:
        return random.randint(1, 100) <= 90  # 90% chance
    elif interest_score >= 60:
        return random.randint(1, 100) <= 60  # 60% chance
    elif interest_score >= 40:
        return random.randint(1, 100) <= 30  # 30% chance
    else:
        return random.randint(1, 100) <= 10  # 10% chance


def calculate_maximum_bid(team_name, player, current_bid, is_human=False):
    """Calculate maximum bid a team is willing to go."""
    team = Team.query.filter_by(team_name=team_name).first()
    if not team:
        return 0
        
    # Available budget after reserving 1 Cr per missing mandatory slot
    available_budget, _ = calculate_budget_reservation(team_name, team.budget)
    
    if is_human:
        # Human team maximum bid is strictly their available budget
        return available_budget
        
    if team_name not in TEAM_PERSONALITIES:
        return available_budget
    
    personality = TEAM_PERSONALITIES[team_name]
    
    # Maximum spend on single player (percentage of available budget)
    max_single_spend = available_budget * personality["max_spend_single_player"]
    
    # Team Requirement Multiplier (Role Urgency)
    role_multiplier = 1.0
    normalized_role = normalize_role(player.role)
    composition = get_team_squad_composition(team_name)
    current_count = composition.get(normalized_role, 0)
    target_min = SQUAD_TARGETS.get(normalized_role, {}).get("min", 0)
    target_max = SQUAD_TARGETS.get(normalized_role, {}).get("max", 15)

    if current_count < target_min:
        role_multiplier = 1.6
    elif current_count >= target_max:
        role_multiplier = 0.6
        max_single_spend *= 0.6

    # Get multiplier from player value engine
    from services.player_value_engine import get_price_multiplier, get_expected_price_range
    base_engine_multiplier = get_price_multiplier(player)
    
    # Apply personality aggression
    aggression = personality.get("aggression", 1.0)
    
    # Auction stage modifier
    _, stage_modifier = get_auction_stage(team_name)
    
    # Calculate max bid
    max_bid = (player.base_price * base_engine_multiplier * aggression * stage_modifier * role_multiplier)
    
    # Auction Pressure System (active bidders dynamically push max bid higher)
    from flask import session
    import json
    from models.auction_session import AuctionSession
    
    try:
        auction_id = session.get("auction_id", "")
        auction = AuctionSession.query.filter_by(auction_id=auction_id).first()
        if auction:
            active_count = len(json.loads(auction.teams_interested)) if auction.teams_interested else 0
            if active_count >= 8:
                max_bid *= 1.45
            elif active_count >= 6:
                max_bid *= 1.30
            elif active_count >= 4:
                max_bid *= 1.15
    except Exception:
        pass
        
    # Star Player Bonus
    if player.rating >= 95:
        max_bid *= random.uniform(1.2, 1.8)
        
    # Allow exceeding max_single_spend for elite players if they really want them
    if player.rating >= 92 and aggression >= 1.2:
        max_single_spend = available_budget * 0.45  # Allow up to 45% of budget for superstars
    
    # Enforce minimums to ensure stars get bid up
    if player.rating >= 92 and available_budget >= 10.0:
        min_expected, max_expected = get_expected_price_range(player.rating)
        # Ensure AI will at least try to bid near minimum expected for superstars if budget allows
        if max_bid < min_expected:
            max_bid = min(min_expected, max_single_spend)
            
    # Cap at available budget and single spend limit
    max_bid = min(max_bid, max_single_spend, available_budget)
    
    return max(current_bid + 0.5, max_bid)  # At least willing to raise by 0.5 Cr


def can_team_join_auction(team_name, player_role=None):
    """Check if team can still participate in auction."""
    squad_size = TeamSquad.query.filter_by(team_name=team_name).count()
    
    # Check if squad is full
    if squad_size >= MAX_SQUAD_SIZE:
        return False
    
    # Check if team has enough budget
    team = Team.query.filter_by(team_name=team_name).first()
    if not team or team.budget < MINIMUM_PLAYER_COST:
        return False
        
    # Check strict role requirements if approaching squad limit
    if player_role:
        normalized_role = normalize_role(player_role)
        composition = get_team_squad_composition(team_name)
        current_count = composition.get(normalized_role, 0)
        target_max = SQUAD_TARGETS.get(normalized_role, {}).get("max", 15)
        
        if current_count >= target_max:
            return False
            
        # If team has exactly the required remaining slots, force role-aware bidding
        slots_left = MAX_SQUAD_SIZE - squad_size
        missing_mandatory_slots = 0
        for r_key, targets in SQUAD_TARGETS.items():
            c_count = composition.get(r_key, 0)
            if c_count < targets.get("min", 0):
                missing_mandatory_slots += (targets.get("min", 0) - c_count)
        
        if 0 < slots_left <= missing_mandatory_slots:
            # We are forced to only buy roles we are short on
            if composition.get(normalized_role, 0) >= SQUAD_TARGETS.get(normalized_role, {}).get("min", 0):
                return False  # Need to save the slot for a missing mandatory role

    return True


def get_bid_increment(bid_value):
    """Calculate bid increment based on current bid."""
    if bid_value < 1.0:
        return 0.1
    elif bid_value < 2.0:
        return 0.2
    elif bid_value < 10.0:
        return 1.0
    else:
        return 2.0
