import os
import requests
import json
from flask import Flask, render_template, request

app = Flask(__name__)

WARDROBE_PATH = os.path.join(os.path.dirname(__file__), 'wardrobe.json')


def load_wardrobe():
    """Load wardrobe config mapping generic labels to custom labels and optional images."""
    try:
        with open(WARDROBE_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def apply_wardrobe_mapping(advice, wardrobe):
    """Apply wardrobe config: replace generic labels and add image paths for display."""
    for key in ['hat', 'coat', 'layer', 'pants', 'shoes']:
        generic = advice.get(key, 'None')
        if generic and generic != 'None' and key in wardrobe:
            item_config = wardrobe[key].get(generic)
            if item_config and isinstance(item_config, dict):
                advice[key + '_label'] = item_config.get('label', generic)
                img = item_config.get('image')
                advice[key + '_image'] = img if img else None
            else:
                advice[key + '_label'] = generic
                advice[key + '_image'] = None
        else:
            advice[key + '_label'] = generic if generic and generic != 'None' else None
            advice[key + '_image'] = None
    # Rebuild outfit oneliner with display labels
    outfit_parts = []
    for key in ['hat', 'coat', 'layer', 'pants', 'shoes']:
        val = advice.get(key + '_label') or advice.get(key)
        if val and val != 'None':
            outfit_parts.append(val)
    advice['outfit_oneliner'] = ' | '.join(outfit_parts) if outfit_parts else (advice.get('layer_label') or advice['layer']) + ' | ' + (advice.get('pants_label') or advice['pants']) + ' | ' + (advice.get('shoes_label') or advice['shoes'])

def get_city_name(lat, lon):
    try:
        headers = {'User-Agent': 'WeatherChap/1.0'}
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10"
        response = requests.get(url, headers=headers)
        data = response.json()
        address = data.get('address', {})
        return address.get('city') or address.get('town') or address.get('village') or "Unknown Location"
    except:
        return "Unknown Location"

def get_weather(lat, lon):
    # Fetching hourly data, current temp, and apparent_temperature (feels_like)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto"
    
    try:
        response = requests.get(url)
        data = response.json()
        daily = data['daily']
        current = data['current']
        
        today = {
            "temp_max": daily['temperature_2m_max'][0],
            "temp_min": daily['temperature_2m_min'][0],
            "precip_prob": daily['precipitation_probability_max'][0],
            "weathercode": daily['weathercode'][0],
            "current_temp": current['temperature_2m'],
            "feels_like": current['apparent_temperature'] 
        }
        return today
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def get_outfit_advice(weather):
    # 1. DETERMINISTIC LOGIC (The Mannequin)
    advice = {
        "text": "Pack a layer, you might need it.",
        "summary": "Layer up + be ready for anything.",
        "color_theme": "#87CEEB",
        "hat": "None",
        "coat": "None",
        "layer": "T-Shirt",
        "pants": "Chinos",
        "socks": "Ankle Socks",
        "shoes": "Vans"
    }

    # Precipitation
    if weather['precip_prob'] > 50:
        advice['text'] = "Rain likely — shell and waterproof shoes."
        advice['summary'] = "Full rain gear — shell + waterproof shoes."
        advice['coat'] = "Rain Shell"
        advice['shoes'] = "Doc Martens"
        advice['color_theme'] = "#778899"
    elif weather['precip_prob'] > 20:
        advice['text'] = "Showers possible — bring a packable shell."
        advice['summary'] = "Layer up + bring a shell."
        advice['coat'] = "Pack Shell"

    # Temperature
    if weather['temp_max'] < 40:
        advice['text'] = "Cold — coat, layers, and warm shoes."
        advice['summary'] = "Full cozy mode — coat, layers, beanie."
        advice['coat'] = "Brown Wool Coat"
        advice['layer'] = "Flannel"
        advice['hat'] = "Beanie"
        advice['socks'] = "Wool Socks"
        advice['color_theme'] = "#B0C4DE"
    elif weather['temp_max'] < 60:
        advice['text'] = "Chilly — layer up with a hoodie."
        advice['summary'] = "Layer up — jacket optional, pack light."
        advice['layer'] = "Hoodie"

    # Build outfit one-liner (non-None items only)
    outfit_parts = []
    for key in ['hat', 'coat', 'layer', 'pants', 'shoes']:
        val = advice.get(key, 'None')
        if val and val != 'None':
            outfit_parts.append(val)
    advice['outfit_oneliner'] = ' | '.join(outfit_parts) if outfit_parts else advice['layer'] + ' | ' + advice['pants'] + ' | ' + advice['shoes']

    # Wardrobe mapping: custom labels from wardrobe.json
    wardrobe = load_wardrobe()
    apply_wardrobe_mapping(advice, wardrobe)

    return advice

@app.route('/')
def home():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    location_label = "Provo (Default)"

    if not lat:
        lat = "40.2338"
        lon = "-111.6585"
    else:
        city = get_city_name(lat, lon)
        location_label = f"{city}"

    weather = get_weather(lat, lon)
    theme = request.args.get('theme', 'light')
    advice = get_outfit_advice(weather)
    
    return render_template('index.html', weather=weather, advice=advice, location_label=location_label,
                          theme=theme, lat=lat, lon=lon)

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=5001)