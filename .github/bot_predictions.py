#!/usr/bin/env python3
import requests
import os
import json
from datetime import datetime
import statistics

# ==================== CONFIG ====================
OWM_KEY = os.getenv("OPENWEATHER_KEY", "808dbe8543e4f9f4e50ae345414decd4")
WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY", "24fd22e1314d4cde8f4123108253110")

ZONAS = {
    "Isla Dragonera": (39.60, 2.30),
    "Isla de Cabrera": (39.17, 2.89),
    "Bahía de Palma": (39.57, 2.73),
    "Portals Vells": (39.52, 2.54),
    "Llucmajor": (39.33, 3.07),
    "Punta Negra": (39.45, 3.00),
    "Cala d'Or": (39.35, 3.40),
    "Porto Cristo": (39.42, 3.41),
    "Cala Millor": (39.49, 3.38),
    "Bahía Pollença": (39.83, 3.09),
    "Alcúdia": (39.85, 3.11),
    "Can Picafort": (39.73, 3.14),
    "Formentor": (39.96, 3.25),
    "Cala Sant Vicenç": (39.88, 3.13),
    "Sóller": (39.77, 2.73),
}

# ==================== APIS ====================

def get_openweather_data(lat, lon):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OWM_KEY}&units=metric"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def get_weatherapi_data(lat, lon):
    try:
        url = f"https://api.weatherapi.com/v1/forecast.json?key={WEATHERAPI_KEY}&q={lat},{lon}&days=3&aqi=no"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

# ==================== PARSEAR ====================

def parse_openweather(data, day_idx):
    if not data or "list" not in data:
        return None
    start_idx = day_idx * 8
    end_idx = min(start_idx + 8, len(data["list"]))
    if start_idx >= len(data["list"]):
        return None
    day_data = data["list"][start_idx:end_idx]
    if not day_data:
        return None
    winds = [item["wind"]["speed"] for item in day_data]
    temps = [item["main"]["temp"] for item in day_data]
    if not winds or not temps:
        return None
    wind_ms = statistics.mean(winds)
    wind_knots = wind_ms * 1.94384
    temp = statistics.mean(temps)
    return {"wind": round(wind_knots, 1), "temp": round(temp, 1)}

def parse_weatherapi(data, day_idx):
    if not data or "forecast" not in data:
        return None
    forecast_days = data["forecast"]["forecastday"]
    if day_idx >= len(forecast_days):
        return None
    day = forecast_days[day_idx]
    if "hour" not in day:
        return None
    hours = day["hour"]
    if not hours:
        return None
    winds = [h.get("wind_kph", 0) for h in hours if "wind_kph" in h]
    temps = [h.get("temp_c", 0) for h in hours if "temp_c" in h]
    if not winds or not temps:
        return None
    wind_kph = max(winds)
    wind_knots = wind_kph * 0.539957
    temp = statistics.mean(temps)
    return {"wind": round(wind_knots, 1), "temp": round(temp, 1)}

# ==================== GUARDAR PREDICCIONES ====================

def save_predictions():
    """Guarda las predicciones actuales para validación futura"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    predictions = {
        "fecha_creacion": today_str,
        "timestamp": now.isoformat(),
        "zonas": {}
    }
    
    print("\n💾 Guardando predicciones para validación futura...\n")
    
    zona_count = 0
    for zona_name, (lat, lon) in ZONAS.items():
        zona_count += 1
        print(f"[{zona_count}/15] 📡 {zona_name}...", end=" ", flush=True)
        
        # Obtener datos de las 2 APIs
        ow_data = get_openweather_data(lat, lon)
        wa_data = get_weatherapi_data(lat, lon)
        
        # Parsear día 0 (HOY) - para validación mañana
        ow_parsed = parse_openweather(ow_data, 0)
        wa_parsed = parse_weatherapi(wa_data, 0)
        
        predictions["zonas"][zona_name] = {
            "openweather": ow_parsed,
            "weatherapi": wa_parsed
        }
        
        print("✅")
    
    # Guardar en archivo
    os.makedirs("predicciones", exist_ok=True)
    filepath = f"predicciones/pred_{today_str}.json"
    
    with open(filepath, "w") as f:
        json.dump(predictions, f, indent=2)
    
    print(f"\n✅ Predicciones guardadas en: {filepath}\n")

# ==================== MAIN ====================

if __name__ == "__main__":
    print("🚀 Bot Predictor - Guardando predicciones...\n")
    save_predictions()
    print("✅ ¡Listo!")
