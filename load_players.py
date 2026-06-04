from app import app
from extensions import db
from models.player import Player
import csv

with app.app_context():

    with open("players.csv", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:

            player = Player(
                name=row["Name"].strip(),
                role=row["Role"].strip(),
                base_price=float(row["BasePrice"]) / 10000000,
                rating=int(row["Rating"])
            )

            db.session.add(player)

        db.session.commit()

print("Players loaded successfully!")