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
    for h in range(9):
        for a in range(9):
            p = poisson(h, home_mean) * poisson(a, away_expectancy if 'away_expectancy' in locals() else away_mean)
            p = poisson(h, home_mean) * poisson(a, away_mean)
            if h > a: prob_home += p
            elif a > h: prob_away += p
            else: prob_draw += p
    return prob_home, prob_draw, prob_away

def find_daily_picks():
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
            matches = response.json()
            
            for match in matches:
                # Default probabilities for a standard game
                p_home, p_draw, p_away = 0.45, 0.25, 0.30 
                
                for bookie in match['bookmakers']:
                    if bookie['key'] in ['pinnacle', 'betfair_ex', 'unibet', 'williamhill']:
                        market = bookie['markets'][0]['outcomes']
                        h_odds = next(o['price'] for o in market if o['name'] == match['home_team'])
                        a_odds = next(o['price'] for o in market if o['name'] == match['away_team'])

                        # If there is a massive favorite, adjust probability to be realistic
                        if h_odds < 1.45: p_home, p_away = 0.70, 0.10
                        elif a_odds < 1.45: p_home, p_away = 0.10, 0.70
                        
                        h_edge = (h_odds * p_home) - 1
                        a_edge = (a_odds * p_away) - 1

                        # Filters for "Professional" value (5% to 25% edge only)
                        if 0.05 < h_edge < 0.25:
                            all_potential_bets.append({'match': f"{match['home_team']} vs {match['away_team']}", 'pick': match['home_team'], 'odds': h_odds, 'edge': h_edge})
                        elif 0.05 < a_edge < 0.25:
                            all_potential_bets.append({'match': f"{match['home_team']} vs {match['away_team']}", 'pick': match['away_team'], 'odds': a_odds, 'edge': a_edge})
        except: continue

    return sorted(all_potential_bets, key=lambda x: x['edge'], reverse=True)[:3]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})

if __name__ == "__main__":
    picks = find_daily_picks()
    if picks:
        msg = "🚀 *AI SCOUT: CALIBRATED DAILY PICKS*\n"
        msg += "Professional Value Analysis Complete.\n\n"
        for p in picks:
            msg += f"🏟 *{p['match']}*\n✅ *Prediction:* {p['pick']}\n📈 *Odds:* {p['odds']}\n💎 *Edge:* {round(p['edge']*100, 2)}%\n\n"
        send_telegram(msg)
    else:
        send_telegram("⚠️ *Scan Complete:* No professional value found in major markets right now.")
