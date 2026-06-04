from extensions import db


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(100), nullable=False, unique=True)
    budget = db.Column(db.Float, nullable=False, default=120.0)

    def to_dict(self):
        return {"id": self.id, "team_name": self.team_name, "budget": self.budget}

    def __repr__(self):
        return f"<Team {self.team_name} - {self.budget}cr>"
