import sqlite3
import os
from services.player_value_engine import get_player_tier
from services.auction_set_manager import get_auction_set_name

db_path = os.path.join(os.path.dirname(__file__), 'database.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def add_column(table, column_name, data_type, default=""):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {data_type}")
        print(f"Added column {column_name}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {column_name} already exists")
        else:
            print(f"Error adding {column_name}: {e}")

# Add new columns
add_column("players", "tier", "VARCHAR(50)")
add_column("players", "auction_set", "VARCHAR(100)")
add_column("players", "auction_round", "VARCHAR(50)")
add_column("players", "manual_tier_lock", "BOOLEAN DEFAULT 0")
add_column("players", "manual_set_lock", "BOOLEAN DEFAULT 0")

conn.commit()

# Backfill data
class PlayerMock:
    def __init__(self, rating, role, base_price):
        self.rating = rating
        self.role = role
        self.base_price = base_price

cursor.execute("SELECT id, rating, role, base_price FROM players")
players = cursor.fetchall()

for p in players:
    p_id, rating, role, base_price = p
    mock = PlayerMock(rating, role, base_price)
    tier = get_player_tier(rating)
    auction_set = get_auction_set_name(mock)
    
    cursor.execute(
        "UPDATE players SET tier = ?, auction_set = ?, manual_tier_lock = 0, manual_set_lock = 0 WHERE id = ?",
        (tier, auction_set, p_id)
    )

conn.commit()
conn.close()

print("Database migration and backfill completed successfully.")
