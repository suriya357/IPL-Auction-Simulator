# IPL Mega Auction Simulator & Analytics Engine

![IPL Auction Simulator Banner](https://via.placeholder.com/1200x400/0b0f19/10B981?text=IPL+Mega+Auction+Simulator)

A full-stack algorithmic simulation platform designed to recreate the chaos, strategy, and mathematics of the Indian Premier League (IPL) Mega Auction.

## 🌟 Key Features

### 1. The Live Broadcast Auction Room
A zero-latency, AJAX-driven live bidding environment designed to look exactly like the Star Sports/Cricbuzz broadcast studio. Features live event tickers, smooth UI transitions, and full-screen splash animations for SOLD/UNSOLD events.

### 2. Autonomous AI Bidding Engine
You compete against 9 AI franchises. The AI isn't random—it's driven by a sophisticated valuation engine:
- **Team Personalities**: RCB heavily prioritizes star batters; PBKS takes high risks; CSK focuses on all-rounders.
- **Role Scarcity**: If an AI team is missing a Wicket Keeper with only 2 slots left, their max budget multiplier dynamically inflates by 1.6x.
- **Auction Pressure**: Bidding wars involving more than 8 teams trigger "FOMO", artificially inflating the player's final sale price up to 1.8x beyond mathematical logic.

### 3. Post-Auction Deep Analytics
Once the auction concludes, the platform analyzes the data:
- **Best Playing XI Generator**: Automatically derives the strongest possible starting 11 for every franchise based on role constraints (min 3 batters, 3 bowlers, 1 WK, 1 AR) and sorting by algorithmic rating.
- **Winner Predictor**: Runs season simulations using a Softmax temperature model to project the IPL Champion, Playoff teams, and Head-to-Head matchups based on Squad Depth, Balance, and Budget Efficiency.
- **Power Rankings**: Live charts (Chart.js) breaking down the highest spenders and the smartest budget-value purchases.

### 4. Admin Management Center
A comprehensive suite for tournament directors:
- Drag-and-Drop (`SortableJS`) interface to manually shift players between Tiers (Superstars vs. Squad Players) and Auction Sets.
- Manual Lock system ensuring AI recalculations respect human overrides.
- Live-Monitor God View and CSV Export functionality.

---

## 🏗 System Architecture

The application operates on a monolithic Flask architecture optimized for speed and state management. 

1. **User Browser (JS/AJAX)**: Polls the auction state at 1000ms intervals. Uses DOMParser to perform zero-flicker HTML component swapping.
2. **Flask Routes**: Manages the multi-tenant simulation state using Server-Side Sessions.
3. **AI Valuation Engine**: Calculates base expectations using `player_value_engine.py` and `ai_engine_v2.py`.
4. **SQLite/PostgreSQL**: Stores the dynamic state of 300+ players and 10 franchise budgets in real-time.

---

## 🚀 Installation & Local Deployment

### Prerequisites
- Python 3.11+
- Git

### Setup
1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ipl-auction-simulator.git
   cd ipl-auction-simulator
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Rename `.env.example` to `.env` and configure your `SECRET_KEY`.

5. **Run the Application**
   ```bash
   python app.py
   ```
   *The platform will be live at http://127.0.0.1:5000*

---

## ☁️ Cloud Deployment (Render)

This repository is pre-configured for Render.
1. Connect your GitHub repository to Render.
2. Select **Web Service**.
3. Render will automatically detect the `render.yaml` configuration and `runtime.txt`.
4. Ensure you set the `DATABASE_URL` environment variable to a managed PostgreSQL instance in the Render dashboard for persistent data.

---

## 🛠 Tech Stack

**Backend**: Python, Flask, SQLAlchemy  
**Database**: SQLite (Local), PostgreSQL (Production)  
**Frontend**: HTML5, CSS3, Bootstrap 5.3, Vanilla JavaScript (ES6)  
**Libraries**: Chart.js, SortableJS, Jinja2  

---

## 🔮 Future Enhancements
- WebSockets (`Flask-SocketIO`) integration to replace AJAX polling for absolute zero-latency multiplayer auctions.
- Player Retention logic (allowing teams to retain 4 players pre-auction).
- Right-To-Match (RTM) card implementation.

*Built with passion by a cricket and data science enthusiast.*
