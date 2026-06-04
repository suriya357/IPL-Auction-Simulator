from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class AuctionResult(db.Model):
    __tablename__ = "auction_results"
    id = db.Column(db.Integer, primary_key=True)
    player_name = db.Column(db.String(200), nullable=False)
    team_name = db.Column(db.String(100), nullable=False)
    sold_price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {"id": self.id, "player_name": self.player_name, "team_name": self.team_name, "sold_price": self.sold_price}


class AuctionEventLog(db.Model):
    __tablename__ = "auction_event_log"
    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.String(100), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    team_name = db.Column(db.String(100), nullable=True)
    player_name = db.Column(db.String(200), nullable=True)
    amount = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "auction_id": self.auction_id,
            "event_type": self.event_type,
            "team_name": self.team_name,
            "player_name": self.player_name,
            "amount": self.amount,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="admin")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
