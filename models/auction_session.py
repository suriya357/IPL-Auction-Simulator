from extensions import db
from datetime import datetime

class AuctionSession(db.Model):
    __tablename__ = "auction_sessions"
    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.String(100), unique=True, nullable=False)
    current_player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=True)
    auction_stage = db.Column(db.String(50), default="ROUND_1")  # ROUND_1, UNSOLD_ROUND, COMPLETED
    auction_state = db.Column(db.String(50), default="OPEN")  # OPEN, GOING_ONCE, GOING_TWICE, FINAL_CALL, SOLD, UNSOLD, PAUSED
    current_bid = db.Column(db.Float, default=0.0)
    highest_bidder = db.Column(db.String(100), nullable=True)
    last_bid_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    countdown_started = db.Column(db.DateTime, nullable=True)
    teams_passed = db.Column(db.Text, default="")  # JSON list of teams that passed
    teams_interested = db.Column(db.Text, default="")  # JSON list of interested teams
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "auction_id": self.auction_id,
            "current_player_id": self.current_player_id,
            "auction_state": self.auction_state,
            "current_bid": self.current_bid,
            "highest_bidder": self.highest_bidder,
            "last_bid_timestamp": self.last_bid_timestamp.isoformat() if self.last_bid_timestamp else None,
            "countdown_started": self.countdown_started.isoformat() if self.countdown_started else None,
        }
