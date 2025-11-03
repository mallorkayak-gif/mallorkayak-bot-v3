#!/usr/bin/env python3
import requests
import os
import json
from datetime import datetime, timedelta
import statistics

# ==================== CONFIG ====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OWM_KEY = os.getenv("OPENWEATHER_KEY", "808dbe8543e4f9f4e50ae345414decd4")
WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY", "24fd22e1314d4cde8f4123108253110")

# Zonas kayak offshore en Mallorca
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

# ==================== FUNCIONES API ====================

def get_openmeteo_data(lat, lon):
    """Obtiene datos de Open-Meteo"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,windspeed_10m_max&timezone=Europe/Madrid&forecast_days=3"
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def get_openweather_data(lat, lon):
    """Obtiene datos de OpenWeatherMap"""
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OWM_KEY}&units=metric"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def get_weatherapi_data(lat, lon):
    """Obtiene datos de Weatherapi"""
    try:
        url = f"https://api.weatherapi.com/v1/forecast.json?key={WEATHERAPI_KEY}&q={lat},{lon}&days=3&aqi=no"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

# ==================== PARSEAR ====================

def parse_openmeteo(data, day_idx):
    if not data or "daily" not in data:
        return None
    daily = data["daily"]
    if day_idx >= len(daily.get("windspeed_10m_max", [])):
        return None
    wind_kph = daily["windspeed_10m_max"][day_idx]
    wind_knots = wind_kph * 0.539957
    temp = daily["temperature_2m_max"][day_idx]
    return {"wind": wind_knots, "temp": temp}

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
    return {"wind": wind_knots, "temp": temp}

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
    return {"wind": wind_knots, "temp": temp}

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
    
    print("\n📊 Guardando predicciones para validación...\n")
    
    for zona_name, (lat, lon) in ZONAS.items():
        # Obtener datos de las 3 APIs
        om_data = get_openmeteo_data(lat, lon)
        ow_data = get_openweather_data(lat, lon)
        wa_data = get_weatherapi_data(lat, lon)
        
        # Parsear día 0 (HOY) - para validación mañana
        om_parsed = parse_openmeteo(om_data, 0)
        ow_parsed = parse_openweather(ow_data, 0)
        wa_parsed = parse_weatherapi(wa_data, 0)
        
        predictions["zonas"][zona_name] = {
            "openmeteo": om_parsed,
            "openweather": ow_parsed,
            "weatherapi": wa_parsed
        }
        
        print(f"  ✅ {zona_name}")
    
    # Guardar en archivo
    os.makedirs("predicciones", exist_ok=True)
    filepath = f"predicciones/pred_{today_str}.json"
    
    with open(filepath, "w") as f:
        json.dump(predictions, f, indent=2)
    
    print(f"\n💾 Predicciones guardadas en: {filepath}")
    return filepath

# ==================== VALIDAR PREDICCIONES ====================

def validate_predictions():
    """Compara predicciones de ayer con datos reales de hoy"""
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    
    pred_file = f"predicciones/pred_{yesterday_str}.json"
    
    # Si no existe archivo de predicciones de ayer, no hay nada que validar
    if not os.path.exists(pred_file):
        print("📂 No hay predicciones de ayer para validar")
        return None
    
    print("\n🔍 Validando predicciones de ayer contra realidad de hoy...\n")
    
    with open(pred_file, "r") as f:
        predictions = json.load(f)
    
    validation = {
        "fecha_validacion": now.strftime("%Y-%m-%d"),
        "prediccion_fecha": yesterday_str,
        "zonas": {},
        "resumen": {"openmeteo": [], "openweather": [], "weatherapi": []}
    }
    
    # Obtener datos reales de hoy
    for zona_name, (lat, lon) in ZONAS.items():
        om_data = get_openmeteo_data(lat, lon)
        ow_data = get_openweather_data(lat, lon)
        wa_data = get_weatherapi_data(lat, lon)
        
        om_real = parse_openmeteo(om_data, 0)
        ow_real = parse_openweather(ow_data, 0)
        wa_real = parse_weatherapi(wa_data, 0)
        
        zona_pred = predictions["zonas"].get(zona_name, {})
        
        validation["zonas"][zona_name] = {}
        
        # Comparar OpenMeteo
        if zona_pred.get("openmeteo") and om_real:
            pred_wind = zona_pred["openmeteo"]["wind"]
            real_wind = om_real["wind"]
            error = abs(pred_wind - real_wind)
            accuracy = max(0, 100 - error * 10)  # Fórmula simple de accuracy
            validation["zonas"][zona_name]["openmeteo"] = {
                "prediccion": round(pred_wind, 1),
                "real": round(real_wind, 1),
                "error": round(error, 1),
                "accuracy": round(accuracy, 1)
            }
            validation["resumen"]["openmeteo"].append(accuracy)
        
        # Comparar OpenWeather
        if zona_pred.get("openweather") and ow_real:
            pred_wind = zona_pred["openweather"]["wind"]
            real_wind = ow_real["wind"]
            error = abs(pred_wind - real_wind)
            accuracy = max(0, 100 - error * 10)
            validation["zonas"][zona_name]["openweather"] = {
                "prediccion": round(pred_wind, 1),
                "real": round(real_wind, 1),
                "error": round(error, 1),
                "accuracy": round(accuracy, 1)
            }
            validation["resumen"]["openweather"].append(accuracy)
        
        # Comparar Weatherapi
        if zona_pred.get("weatherapi") and wa_real:
            pred_wind = zona_pred["weatherapi"]["wind"]
            real_wind = wa_real["wind"]
            error = abs(pred_wind - real_wind)
            accuracy = max(0, 100 - error * 10)
            validation["zonas"][zona_name]["weatherapi"] = {
                "prediccion": round(pred_wind, 1),
                "real": round(real_wind, 1),
                "error": round(error, 1),
                "accuracy": round(accuracy, 1)
            }
            validation["resumen"]["weatherapi"].append(accuracy)
    
    # Guardar validación
    os.makedirs("validaciones", exist_ok=True)
    val_file = f"validaciones/val_{yesterday_str}.json"
    
    with open(val_file, "w") as f:
        json.dump(validation, f, indent=2)
    
    print(f"✅ Validación guardada en: {val_file}")
    return validation

# ==================== GENERAR REPORTE ====================

def send_validation_report(validation):
    """Envía reporte de validación a Telegram"""
    if not validation:
        return
    
    # Calcular promedios
    om_avg = statistics.mean(validation["resumen"]["openmeteo"]) if validation["resumen"]["openmeteo"] else 0
    ow_avg = statistics.mean(validation["resumen"]["openweather"]) if validation["resumen"]["openweather"] else 0
    wa_avg = statistics.mean(validation["resumen"]["weatherapi"]) if validation["resumen"]["weatherapi"] else 0
    
    msg = f"📊 VALIDACIÓN DE PREDICCIONES\n"
    msg += f"Predicción: {validation['prediccion_fecha']}\n"
    msg += f"Validación: {validation['fecha_validacion']}\n"
    msg += "═" * 50 + "\n\n"
    
    msg += "🏆 RANKING DE PRECISIÓN:\n"
    apis = [
        ("🔵 OpenWeatherMap", ow_avg),
        ("🟢 Weatherapi", wa_avg),
        ("🟡 Open-Meteo", om_avg)
    ]
    apis.sort(key=lambda x: x[1], reverse=True)
    
    for i, (api_name, accuracy) in enumerate(apis):
        msg += f"{i+1}. {api_name}: {accuracy:.1f}%\n"
    
    msg += "\n" + "═" * 50 + "\n"
    msg += "💡 RECOMENDACIÓN:\n"
    if apis[0][1] > 0:
        msg += f"✅ Usar principalmente: {apis[0][0]}\n"
        msg += f"⚠️ Evitar: {apis[2][0]}\n"
    
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
        r = requests.post(url, json=data, timeout=10)
        if r.status_code == 200:
            print("✅ Reporte de validación enviado a Telegram")
        else:
            print(f"❌ Error enviando reporte: {r.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

# ==================== MAIN ====================

if __name__ == "__main__":
    print("🚀 Iniciando sistema de validación de predicciones...\n")
    
    # PASO 1: Validar predicciones de ayer
    validation = validate_predictions()
    if validation:
        send_validation_report(validation)
    
    # PASO 2: Guardar predicciones de hoy para mañana
    save_predictions()
    
    print("\n✅ ¡Sistema de validación completado!")
