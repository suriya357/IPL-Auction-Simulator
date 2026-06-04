from extensions import db


class TeamSquad(db.Model):
    __tablename__ = "team_squads"
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(100), nullable=False)
    player_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "team_name": self.team_name,
            "player_name": self.player_name,
            "role": self.role,
            "purchase_price": self.purchase_price,
        }
