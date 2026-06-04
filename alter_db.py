import sqlite3

def alter():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE auction_sessions ADD COLUMN auction_stage VARCHAR(50) DEFAULT 'ROUND_1'")
        conn.commit()
        print("Successfully added auction_stage column.")
    except Exception as e:
        print(f"Error: {e}")
    conn.close()

if __name__ == '__main__':
    alter()
