from extensions import db


class Player(db.Model):
    __tablename__ = "players"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="available")
    sold_price = db.Column(db.Float, nullable=True)
    sold_to = db.Column(db.String(100), nullable=True)
    tier = db.Column(db.String(50), nullable=True)
    auction_set = db.Column(db.String(100), nullable=True)
    auction_round = db.Column(db.String(50), nullable=True)
    manual_tier_lock = db.Column(db.Boolean, default=False)
    manual_set_lock = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "base_price": self.base_price,
            "rating": self.rating,
            "status": self.status,
            "sold_price": self.sold_price,
            "sold_to": self.sold_to,
            "tier": self.tier,
            "auction_set": self.auction_set,
            "auction_round": self.auction_round,
            "manual_tier_lock": self.manual_tier_lock,
            "manual_set_lock": self.manual_set_lock,
        }

    def __repr__(self):
        return f"<Player {self.name} ({self.role}) - {self.base_price}cr>"
