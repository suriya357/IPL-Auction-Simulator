def get_auction_set_name(player):
    """
    Determine the logical auction set for a player based on rating and role.
    This simulates the real IPL Mega Auction player sets.
    """
    rating = player.rating
    role = player.role.strip().upper() if player.role else "UNKNOWN"
    
    if rating >= 92:
        return "SET 1: MARQUEE PLAYERS"
    
    if rating >= 85:
        if "BATTER" in role or "BATSMAN" in role:
            return "SET 2: ELITE BATTERS"
        if "BOWLER" in role:
            return "SET 3: ELITE BOWLERS"
        if "ALL" in role:
            return "SET 4: ELITE ALL-ROUNDERS"
        if "KEEPER" in role or "WK" in role:
            return "SET 5: WICKET KEEPERS"
            
    if rating >= 75:
        return "SET 6: EMERGING PLAYERS"
        
    if player.base_price and player.base_price <= 0.2:
        return "SET 7: UNCAPPED PLAYERS"
        
    return "SET 8: REMAINING PLAYERS"
