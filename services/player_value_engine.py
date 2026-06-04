import random

def get_player_tier(rating):
    """Determine the tier of a player based on their rating."""
    if rating >= 92:
        return "Tier 1: Superstar"
    elif rating >= 85:
        return "Tier 2: Star"
    elif rating >= 75:
        return "Tier 3: Quality Player"
    else:
        return "Tier 4: Squad Player"

def get_expected_price_range(rating):
    """Return the expected min and max price range for a player."""
    if rating >= 92:
        return (8.0, 25.0)
    elif rating >= 85:
        return (4.0, 15.0)
    elif rating >= 75:
        return (1.0, 8.0)
    else:
        return (0.2, 5.0)

def get_price_multiplier(player):
    """Calculate the base multiplier a player should attract over their base price."""
    rating = player.rating
    min_price, max_price = get_expected_price_range(rating)
    
    # Randomly target a price within their tier bracket
    target_price = random.uniform(min_price, max_price)
    
    if player.base_price > 0:
        return max(1.0, target_price / player.base_price)
    return 1.0
