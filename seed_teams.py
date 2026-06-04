from app import app
from extensions import db
from models.team import Team

with app.app_context():
    team_count = Team.query.count()
    if team_count == 0:
        teams = ["CSK", "MI", "RCB", "KKR", "SRH", "DC", "GT", "RR", "LSG", "PBKS"]
        for t in teams:
            team = Team(team_name=t, budget=120.0)
            db.session.add(team)
        db.session.commit()
        print("10 IPL Teams seeded successfully!")
    else:
        print(f"{team_count} Teams already exist. No seeding required.")
