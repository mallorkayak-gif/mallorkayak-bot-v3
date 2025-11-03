#!/usr/bin/env python3
import requests
import os
from datetime import datetime, timedelta
import statistics

# ==================== CONFIG ====================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
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

# ==================== MAIN ====================

def generate_report():
    """Genera reporte de 3 días"""
    now = datetime.now()
    dias = {}
    
    print("\n📊 Consultando 2 APIs (OpenWeatherMap + Weatherapi)...\n")
    
    for day_idx in range(3):
        día_fecha = now + timedelta(days=day_idx)
        dias[day_idx] = {
            "fecha": día_fecha.strftime("%d/%m"),
            "nombre_dia": ["HOY", "MAÑANA", "PASADO MAÑANA"][day_idx],
            "zonas": []
        }
    
    zona_count = 0
    for zona_name, (lat, lon) in ZONAS.items():
        zona_count += 1
        print(f"[{zona_count}/15] 📡 {zona_name}...", end=" ", flush=True)
        
        # Obtener datos de 2 APIs (sin Open-Meteo)
        ow_data = get_openweather_data(lat, lon)
        wa_data = get_weatherapi_data(lat, lon)
        
        print("✅")
        
        for day_idx in range(3):
            ow_parsed = parse_openweather(ow_data, day_idx)
            wa_parsed = parse_weatherapi(wa_data, day_idx)
            
            # Calcular promedio si tenemos al menos 1 API
            valid_data = {}
            if ow_parsed:
                valid_data["openweather"] = ow_parsed
            if wa_parsed:
                valid_data["weatherapi"] = wa_parsed
            
            if not valid_data:
                continue
            
            winds = [v["wind"] for v in valid_data.values()]
            temps = [v["temp"] for v in valid_data.values()]
            
            avg_wind = statistics.mean(winds)
            avg_temp = statistics.mean(temps)
            confidence = len(valid_data) / 2 * 100
            
            # Calcular score
            if avg_wind > 10:
                score, rating = 2, "🔴 PELIGROSO"
            elif avg_wind > 7:
                score, rating = 4, "🟠 REGULAR"
            elif avg_wind > 5:
                score, rating = 7, "🟡 BUENO"
            else:
                score, rating = 10, "🟢 EXCELENTE"
            
            dias[day_idx]["zonas"].append({
                "nombre": zona_name,
                "wind": avg_wind,
                "temp": avg_temp,
                "score": score,
                "rating": rating,
                "confidence": confidence,
                "sources": len(valid_data)
            })
    
    print("\n✅ ¡Consultas completadas!\n")
    
    # Ordenar zonas por score
    for day_idx in dias:
        dias[day_idx]["zonas"].sort(key=lambda x: x["score"], reverse=True)
    
    # Encontrar mejor día
    best_day = None
    best_score = 0
    best_zona = None
    
    for day_idx in dias:
        if dias[day_idx]["zonas"]:
            top_zona = dias[day_idx]["zonas"][0]
            if top_zona["score"] > best_score:
                best_score = top_zona["score"]
                best_day = day_idx
                best_zona = top_zona
    
    # Construir mensaje
    msg = f"🎣 RECOMENDACIONES KAYAK OFFSHORE - MALLORCA\n"
    msg += f"📅 {now.strftime('%d de %B de %Y')} | {now.strftime('%H:%M')}\n"
    msg += f"🔗 Media de 2 APIs: OpenWeatherMap + Weatherapi\n"
    msg += "═" * 50 + "\n\n"
    
    for day_idx in range(3):
        day_info = dias[day_idx]
        msg += f"📌 {day_info['nombre_dia']} {day_info['fecha']}\n"
        
        if day_info["zonas"]:
            for i, zona in enumerate(day_info["zonas"]):
                msg += f"  {i+1}. {zona['nombre']} - {zona['wind']:.1f}kn {zona['rating']}\n"
        else:
            msg += "  ⚠️ Sin datos\n"
        
        msg += "─" * 50 + "\n"
    
    msg += "═" * 50 + "\n"
    
    if best_zona:
        msg += f"🎯 MEJOR DÍA PARA OFFSHORE:\n"
        msg += f"   📅 {['HOY', 'MAÑANA', 'PASADO MAÑANA'][best_day]} ({dias[best_day]['fecha']})\n"
        msg += f"   📍 {best_zona['nombre']}\n"
        msg += f"   ⭐ Puntuación: {best_zona['score']}/10 {best_zona['rating']}\n"
        msg += f"   💨 Viento: {best_zona['wind']:.1f} nudos\n"
        msg += f"   🌡️ Temp: {best_zona['temp']:.0f}°C\n"
    
    msg += "\n💡 CONSEJOS:\n"
    msg += "   • Consulta SIEMPRE las condiciones locales antes de salir\n"
    msg += "   • Llevar: Traje neopreno 3-5mm, casco, GPS, silbato\n"
    msg += "   • NUNCA salir solo en offshore\n"
    msg += "   • Avisa a alguien tu ruta y hora de retorno\n"
    msg += f"🔗 Fuente: OpenWeatherMap + Weatherapi\n"
    
    return msg

# ==================== TELEGRAM ====================

def send_to_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
        r = requests.post(url, json=data, timeout=10)
        
        if r.status_code == 200:
            print("✅ Mensaje enviado a Telegram")
        else:
            print(f"❌ Error Telegram: {r.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

# ==================== MAIN ====================

if __name__ == "__main__":
    print("🚀 Iniciando bot (versión simplificada)...\n")
    
    if not TOKEN or not CHAT_ID:
        print("❌ Error: credenciales no configuradas")
        exit(1)
    
    report = generate_report()
    print(report)
    
    print("\n📤 Enviando a Telegram...")
    send_to_telegram(report)
    
    print("✅ ¡Bot completado!")
