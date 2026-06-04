# Phase 4.1 - Realistic IPL Auction Economics & Event-Driven AI Bidding

## Overview

Phase 4.1 refactors the IPL Auction Simulator to implement realistic auction economics, intelligent AI bidding strategies, and an event-driven architecture that simulates actual IPL auction behavior.

## Key Improvements Over Phase 4

### 1. **Realistic Squad Management**
- **Squad Size Constraints:** 11-15 players per team
- **Role-Based Targeting:**
  - Batters: 4-6
  - Bowlers: 4-6
  - All-Rounders: 2-4
  - Wicket Keepers: 1-2
- **AI actively builds balanced squads** instead of random purchases

### 2. **Budget Reservation Logic**
- Teams cannot spend their entire budget on one player
- **Formula:**
  ```
  Available Budget = Total Budget - (Remaining Slots × Minimum Player Cost)
  ```
- Example: If a team needs 5 more players and has 50 Cr budget:
  - Reserve: 5 × 1 Cr = 5 Cr
  - Available: 50 - 5 = 45 Cr for bidding

### 3. **Dynamic Maximum Bid Calculation**
Each team calculates max bid for every player based on:
- Player rating (higher rating = higher max bid)
- Role need (needed roles = aggressive bidding)
- Remaining budget (health check)
- Remaining squad slots
- Team personality
- Auction stage (early/mid/late)

### 4. **Team Personalities** (Unique Bidding Behaviors)
```
CSK (Conservative)
- Prefers squad balance (15% max spend per player)
- Weights rating: 30%, role: 30%, budget: 25%, balance: 15%

MI (Aggressive)
- Will spend up to 25% of budget on star players
- Weights rating: 50%, role: 20%, budget: 15%, balance: 15%

RCB (Batter-Focused)
- Strong preference for high-rated batters
- Weights role heavily: 40%

SRH (Bowler-Focused)
- Targets quality bowlers
- Weights role: 40%

GT (Budget-Conscious)
- Conservative spending (12% max per player)
- Weights budget: 30%
```

### 5. **Event-Driven Auction Model**
Replaces turn-based bidding with realistic flow:

```
State Flow:
OPEN (Any interested team can bid)
  ↓
GOING_ONCE (No bid for 2 seconds)
  ↓
GOING_TWICE (No bid for 2 more seconds)
  ↓
FINAL_CALL (No bid for 2 more seconds)
  ↓
SOLD or UNSOLD
```

**Example Auction Sequence:**
```
Time 0:00   - Auction Opens (Player: Virat Kohli, Rating: 95)
Time 0:05   - MI bids ₹10 Cr
Time 0:10   - RCB bids ₹12 Cr
Time 0:15   - CSK passes
Time 0:20   - MI passes
Time 0:25   - Auctioneer: "Going Once!"
Time 0:27   - RCB passes (No more bids)
Time 0:30   - Auctioneer: "Going Twice!"
Time 0:32   - (Silence)
Time 0:35   - Auctioneer: "Final Call!"
Time 0:37   - (Silence)
Time 0:40   - Auctioneer: "SOLD to RCB for ₹12 Cr!"
```

### 6. **Interest Score Calculation**
```
Interest Score = 
  40% × Rating Score +
  25% × Role Need Score +
  20% × Budget Health Score +
  10% × Squad Balance Score +
  5% × Random Factor

Score Range: 0-100
```

### 7. **Interest Thresholds**
```
Score ≥ 80  → 90% probability of bidding (Aggressive)
Score 60-79 → 60% probability of bidding (Normal)
Score 40-59 → 30% probability of bidding (Interested)
Score < 40  → 10% probability of bidding (Pass)
```

### 8. **Unsold Player Mechanism**
- Players can be unsold if no team bids
- Stored as: `status = "unsold"`, `sold_to = NULL`, `sold_price = 0`
- Displayed in dashboard

### 9. **Auction Stages & Modifiers**
```
EARLY STAGE (Squad 0-5): 1.2× max bid modifier (aggressive spending)
MID STAGE (Squad 6-10): 1.0× max bid modifier (balanced)
LATE STAGE (Squad 11-15): 0.7× max bid modifier (conservative)
```

## Database Schema (Phase 4.1)

### New Table: `auction_sessions`
```sql
CREATE TABLE auction_sessions (
  id INTEGER PRIMARY KEY,
  auction_id VARCHAR(100) UNIQUE,
  current_player_id INTEGER FK,
  auction_state VARCHAR(50),  -- OPEN, GOING_ONCE, GOING_TWICE, FINAL_CALL, SOLD, UNSOLD
  current_bid FLOAT,
  highest_bidder VARCHAR(100),
  last_bid_timestamp DATETIME,
  countdown_started DATETIME,
  teams_passed TEXT,  -- JSON list
  teams_interested TEXT,  -- JSON list
  created_at DATETIME
)
```

### Updated `players` Table
```sql
ALTER TABLE players ADD COLUMN status TEXT DEFAULT 'available';  -- available, sold, unsold
ALTER TABLE players ADD COLUMN sold_price FLOAT;
ALTER TABLE players ADD COLUMN sold_to VARCHAR(100);
```

## Architecture

```
routes/auction_routes_v2.py
├── /auction/v2              → Display live auction room
├── /bid/v2                  → Place human bid
├── /pass/v2                 → Human passes
├── /squad/v2                → View squad
└── /auction/state           → API for polling (frontend compatibility)

models/ai_engine_v2.py
├── calculate_interest_score()
├── calculate_maximum_bid()
├── can_team_join_auction()
├── get_team_squad_composition()
├── calculate_budget_reservation()
└── get_auction_stage()

models/auction_session.py
└── AuctionSession model (tracks auction state)
```

## Key Functions

### `calculate_interest_score(team_name, player, current_bid)`
Returns 0-100 score based on:
- Player rating
- Role need
- Budget health
- Squad balance
- Team personality modifiers

### `calculate_maximum_bid(team_name, player, current_bid)`
Returns maximum bid based on:
- Available budget (after reservation)
- Player rating multiplier
- Team personality max spend %
- Auction stage modifier

### `can_team_join_auction(team_name)`
Checks:
- Squad size < MAX_SQUAD_SIZE
- Budget ≥ MINIMUM_PLAYER_COST

### `get_auction_stage(team_name)`
Returns:
- Stage: "EARLY", "MID", or "LATE"
- Modifier: 1.2, 1.0, or 0.7

## Testing Instructions

### 1. Start Application
```bash
cd C:\Users\ganes\Downloads\IPL_Auction
python app.py
```

### 2. Access Auction
- Navigate to: `http://127.0.0.1:5000/select-team`
- Select a team (e.g., RCB)
- Join auction → redirects to `/auction/v2`

### 3. Test Features

**A) Realistic Bidding**
- Bid on high-rating player
- Observe AI teams bidding with varying intensity
- Some teams should pass if max bid reached

**B) Budget Reservation**
- Check "Your Team" remaining budget
- Bid aggressively early
- Observe conservative bidding late in auction

**C) Auctioneer Countdown**
- Place a bid
- Wait 2 seconds → "Going Once"
- Wait 2 more → "Going Twice"
- Wait 2 more → "Final Call"
- If no bid → "SOLD" or "UNSOLD"

**D) Unsold Players**
- Try to find an unsold player in Event Log
- Check Dashboard for unsold count

**E) Squad Balance**
- View squad composition in right panel
- Observe role distribution targeting
- Note progress bars showing role fulfillment

**F) Team Personalities**
- Run multiple auctions
- RCB should focus on high-rating batters
- GT should be budget-conscious (fewer bids)
- MI should bid aggressively

### 4. Dashboard Verification
```
http://127.0.0.1:5000/dashboard
```
- Verify team budgets decrease correctly
- Check squad composition targets met
- View unsold players list

### 5. Auction History
```
http://127.0.0.1:5000/auction-history
```
- Filter by team, role, price range
- Export CSV/Excel

## Validation Checklist

- [ ] No team spends >25% of budget on single player (CSK) or >25% (MI)
- [ ] All teams end with 11-15 players
- [ ] Role targets respected (e.g., 4-6 batters, 4-6 bowlers)
- [ ] Unsold players properly marked and counted
- [ ] Auctioneer countdown works (GOING_ONCE → GOING_TWICE → FINAL_CALL)
- [ ] Event log shows all events including countdown
- [ ] Budget never becomes negative
- [ ] Teams stop bidding when max_bid reached
- [ ] Squad composition shows correct role distribution
- [ ] Dashboard reflects unsold count and auction value

## Frontend Compatibility (for Phase 5 UI enhancements)

The `/auction/state` API endpoint supports polling for real-time updates:

```javascript
fetch('/auction/state')
  .then(response => response.json())
  .then(data => {
    // Returns: player_name, player_rating, current_bid,
    // highest_bidder, auction_state, remaining_budget, countdown_elapsed
  });
```

Polling interval: 2 seconds (matches countdown duration)

This allows frontend to:
- Display live AI bids without page refresh
- Animate countdown timer
- Show real-time budget updates
- Display interested teams dynamically

## Example Auction Simulation Output

```
=== Auction Started ===
Player: Virat Kohli | Rating: 95/100 | Role: Batter | Base: ₹5.00 Cr

T+0:00  RCB (Interest: 92/100) bids ₹5.00 Cr
T+0:05  MI (Interest: 88/100) bids ₹6.00 Cr
T+0:10  KKR (Interest: 75/100) bids ₹7.00 Cr
T+0:15  CSK (Interest: 42/100) PASSES
T+0:20  RCB (Interest: 92/100) bids ₹8.00 Cr
T+0:25  MI (Interest: 88/100) bids ₹9.00 Cr
T+0:30  KKR (Interest: 75/100) bids ₹10.00 Cr
T+0:35  RCB (Interest: 92/100) bids ₹11.00 Cr
T+0:40  MI (Interest: 88/100) PASSES
T+0:45  KKR (Interest: 75/100) PASSES
T+0:50  Auctioneer: "Going Once!"
T+0:55  (No bid)
T+1:00  Auctioneer: "Going Twice!"
T+1:05  (No bid)
T+1:10  Auctioneer: "Final Call!"
T+1:15  (No bid)
T+1:20  SOLD to RCB for ₹11.00 Cr

RCB Remaining Budget: 109.00 Cr (from 120.00)
RCB Squad: 1/15 (1 Batter, 0 Bowlers, 0 All-Rounders, 0 WK)

=== Next Player ===
Player: Rohit Sharma | Rating: 92/100 | Role: Batter | Base: ₹4.50 Cr
...
```

## Performance Considerations

- **Auction State Queries**: O(1) via primary key
- **Squad Composition**: O(n) where n = squad size (~15)
- **Interest Score Calc**: O(1) all lookups cached
- **Auctioneer Logic**: Timestamp-based, no loops
- **Event Log**: Capped at 50 events per auction

## Future Enhancements (Phase 5+)

1. **Real-time Frontend**
   - WebSocket/Server-Sent Events for live bids
   - Animated countdown timer
   - Sound effects for bids

2. **Advanced Analytics**
   - Squad strength ratings
   - Spending efficiency metrics
   - Team comparison dashboards

3. **Multiplayer Auctions**
   - Multiple human players competing
   - Team selection conflicts
   - Real-time scoreboard

4. **Auction Replays**
   - Save full auction sessions
   - Replay with timeline scrubbing
   - Performance analysis

## Known Limitations

1. Countdown is timer-based (not real-time websocket)
2. AI decisions made synchronously (not concurrent bidding)
3. No support for team coalitions or player exclusions
4. Auction stage modifiers are linear (could be more sophisticated)

## Support & Debugging

**Enable Debug Logging:**
```python
# In routes/auction_routes_v2.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check Database State:**
```python
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from models.auction_session import AuctionSession
    sessions = AuctionSession.query.all()
    for s in sessions:
        print(f'Auction {s.auction_id}: {s.auction_state}')
"
```

**Validate Team Budgets:**
```python
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from models.team import Team
    from models.squad import TeamSquad
    for team in Team.query.all():
        spent = sum(s.purchase_price for s in TeamSquad.query.filter_by(team_name=team.team_name).all())
        print(f'{team.team_name}: Budget={team.budget:.2f} Cr, Spent={spent:.2f} Cr, Remaining={120-spent:.2f} Cr')
"
```
