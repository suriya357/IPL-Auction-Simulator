from app import app
from extensions import db
from models.player import Player
from models.ai_engine_v2 import normalize_role

def run_validation():
    with app.app_context():
        players = Player.query.all()
        roles_found = set()
        print("="*50)
        print("ROLE NORMALIZATION VALIDATION REPORT")
        print("="*50)
        for player in players:
            roles_found.add(player.role)
        
        print(f"Total Players Found: {len(players)}")
        print("\nUnique Roles Found in DB:")
        for role in roles_found:
            norm_role = normalize_role(role)
            if role != norm_role:
                print(f"[CHANGE] '{role}' -> '{norm_role}'")
            else:
                print(f"[OK]     '{role}' -> '{norm_role}'")
                
        print("="*50)

if __name__ == "__main__":
    run_validation()
