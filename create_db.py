import csv
from sqlalchemy import inspect, text
from app import create_app
from extensions import db
from models.player import Player
from models.team import Team
from models.auction import User, AuctionEventLog
from models.squad import TeamSquad
from models.auction_session import AuctionSession


def init_db():
    app = create_app()
    with app.app_context():
        db.create_all()

        inspector = inspect(db.engine)
        player_cols = [col["name"] for col in inspector.get_columns("players")] if inspector.has_table("players") else []

        if "status" not in player_cols:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE players ADD COLUMN status TEXT DEFAULT 'available'"))
        if "sold_price" not in player_cols:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE players ADD COLUMN sold_price FLOAT"))
        if "sold_to" not in player_cols:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE players ADD COLUMN sold_to TEXT"))

        # seed admin user if not exists
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)

        # seed default IPL teams (if not present)
        teams = [
            "CSK",
            "MI",
            "RCB",
            "KKR",
            "SRH",
            "DC",
            "GT",
            "PBKS",
            "RR",
            "LSG",
        ]
        for t in teams:
            if not Team.query.filter_by(team_name=t).first():
                team = Team(team_name=t, budget=120.0)
                db.session.add(team)

        # seed players from players.csv if table empty
        if Player.query.count() == 0:
            try:
                with open("players.csv", newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        name = row.get("name") or row.get("Name")
                        role = row.get("role") or row.get("Role")
                        raw_price = float(row.get("base_price") or row.get("BasePrice") or 0)
                        base_price = raw_price / 10000000.0
                        rating = int(row.get("rating") or row.get("Rating") or 50)
                        p = Player(name=name, role=role, base_price=base_price, rating=rating)
                        db.session.add(p)
            except FileNotFoundError:
                print("players.csv not found — skipping player seeding")

        db.session.commit()


if __name__ == "__main__":
    init_db()
    print("Database initialized and seeded.")
