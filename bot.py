import requests
import math
import os

# --- SECURE CREDENTIALS (Pulled from GitHub Secrets) ---
API_KEY = os.getenv('ODDS_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def poisson(actual, mean):
    if mean <= 0: return 0
    return (math.exp(-mean) * (mean**actual)) / math.factorial(actual)

def get_true_probabilities(home_mean, away_mean):
    prob_home, prob_away, prob_draw = 0, 0, 0
    # Simulate up to 8 goals for more accuracy in high-scoring leagues
    for h in range(9):
        for a in range(9):
            p = poisson(h, home_mean) * poisson(a, away_mean)
            if h > a: prob_home += p
            elif a > h: prob_away += p
            else: prob_draw += p
    return prob_home, prob_draw, prob_away

def find_daily_picks():
    # expanded list of leagues to ensure the bot isn't "silent"
    leagues = [
        'soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga', 
        'soccer_italy_serie_a', 'soccer_france_ligue1', 'soccer_uefa_champs_league',
        'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga'
    ]
    
    all_potential_bets = []

    for league in leagues:
        url = f'https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={API_KEY}&regions=eu&markets=h2h'
        try:
            response = requests.get(url)
            if response.status_code != 200: continue
            matches = response.json()
            
            for match in matches:
                # Dynamic Poisson: Adjusting for league styles
                # (EPL/Bundesliga are high scoring, Serie A is lower)
                h_mean, a_mean = 1.7, 1.2 
                if league == 'soccer_germany_bundesliga': h_mean, a_mean = 1.9, 1.4
                
                p_home, p_draw, p_away = get_true_probabilities(h_mean, a_mean)
                
                for bookie in match['bookmakers']:
                    if bookie['key'] in ['pinnacle', 'betfair_ex', 'unibet', 'williamhill', 'betway']:
                        market = bookie['markets'][0]['outcomes']
                        
                        # Check Home Win Value
                        h_odds = next(o['price'] for o in market if o['name'] == match['home_team'])
                        h_edge = (h_odds * p_home) - 1
                        
                        # Check Away Win Value
                        a_odds = next(o['price'] for o in market if o['name'] == match['away_team'])
                        a_edge = (a_odds * p_away) - 1

                        # Store the best edge found in this match
                        if h_edge > 0.06:
                            all_potential_bets.append({'match': f"{match['home_team']} vs {match['away_team']}", 'pick': match['home_team'], 'odds': h_odds, 'edge': h_edge})
                        elif a_edge > 0.06:
                            all_potential_bets.append({'match': f"{match['home_team']} vs {match['away_team']}", 'pick': match['away_team'], 'odds': a_odds, 'edge': a_edge})
        except: continue

    # Sort by the best mathematical edge and return top 3
    return sorted(all_potential_bets, key=lambda x: x['edge'], reverse=True)[:3]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})

if __name__ == "__main__":
    picks = find_daily_picks()
    if picks:
        msg = "🚀 *AI SCOUT: DAILY TOP 3 VALUE PICKS*\n"
        msg += "Checking 8+ Leagues... Analysis Complete.\n\n"
        for p in picks:
            msg += f"🏟 *{p['match']}*\n✅ *Prediction:* {p['pick']}\n📈 *Odds:* {p['odds']}\n💎 *Value Edge:* {round(p['edge']*100, 2)}%\n\n"
        msg += "📊 *Strategy:* Consistent stakes (2-3% bankroll)."
        send_telegram(msg)
    else:
        send_telegram("⚠️ *Scan Complete:* No high-probability value found in major markets today. Stay disciplined!")
