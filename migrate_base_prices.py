from app import app
from extensions import db
from models.player import Player

with app.app_context():
    players = Player.query.all()
    updated_count = 0
    for player in players:
        if player.base_price > 1000:
            player.base_price /= 10000000
            updated_count += 1
            
    db.session.commit()
    print(f"Migrated {updated_count} players to Crores.")
