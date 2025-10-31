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
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,windspeed_10m_max,waveheight_max&timezone=Europe/Madrid&forecast_days=3"
        r = requests.get(url, timeout=20)  # Aumentado a 20s
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        pass  # Sin mensajes de error para no saturar logs
    return None

def get_openweather_data(lat, lon):
    """Obtiene datos de OpenWeatherMap"""
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OWM_KEY}&units=metric"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        pass
    return None

def get_weatherapi_data(lat, lon):
    """Obtiene datos de Weatherapi"""
    try:
        url = f"https://api.weatherapi.com/v1/forecast.json?key={WEATHERAPI_KEY}&q={lat},{lon}&days=3&aqi=no"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        pass
    return None

# ==================== PARSEAR DATOS ====================

def parse_openmeteo(data, day_idx):
    """Parsea Open-Meteo para día específico"""
    if not data or "daily" not in data:
        return None
    daily = data["daily"]
    if day_idx >= len(daily.get("windspeed_10m_max", [])):
        return None
    
    wind_kph = daily["windspeed_10m_max"][day_idx]
    wind_knots = wind_kph * 0.539957  # Convertir a nudos
    temp = daily["temperature_2m_max"][day_idx]
    wave = daily.get("waveheight_max", [0])[day_idx] if "waveheight_max" in daily else 0
    
    return {"wind": wind_knots, "temp": temp, "wave": wave}

def parse_openweather(data, day_idx):
    """Parsea OpenWeatherMap para día específico"""
    if not data or "list" not in data:
        return None
    
    # OpenWeatherMap da datos cada 3 horas. Tomar día completo (8 puntos = 24h)
    start_idx = day_idx * 8
    end_idx = start_idx + 8
    
    if end_idx > len(data["list"]):
        return None
    
    day_data = data["list"][start_idx:end_idx]
    
    winds = [item["wind"]["speed"] for item in day_data]  # m/s
    temps = [item["main"]["temp"] for item in day_data]
    
    wind_ms = statistics.mean(winds)
    wind_knots = wind_ms * 1.94384  # m/s a nudos
    temp = statistics.mean(temps)
    
    return {"wind": wind_knots, "temp": temp, "wave": 0}  # OpenWeather no da olas

def parse_weatherapi(data, day_idx):
    """Parsea Weatherapi para día específico"""
    if not data or "forecast" not in data:
        return None
    
    forecast_days = data["forecast"]["forecastday"]
    if day_idx >= len(forecast_days):
        return None
    
    day = forecast_days[day_idx]
    
    # Extraer viento máximo del día
    hours = day["hour"]
    winds = [h["wind_kph"] for h in hours]
    temps = [h["temp_c"] for h in hours]
    
    wind_kph = max(winds)
    wind_knots = wind_kph * 0.539957
    temp = statistics.mean(temps)
    
    return {"wind": wind_knots, "temp": temp, "wave": 0}  # Weatherapi no da olas

# ==================== LOGIC PRINCIPAL ====================

def fetch_all_data_for_zone(zona_name, lat, lon, retries=2):
    """Obtiene datos de las 3 APIs para una zona (SECUENCIAL con reintentos)"""
    results = {}
    
    # Intentar cada API por separado (secuencial para no sobrecargar)
    print(f"  📡 {zona_name}...", end=" ", flush=True)
    
    # 1. OpenWeatherMap (más rápida, intentar primero)
    for attempt in range(retries):
        try:
            results["openweather"] = get_openweather_data(lat, lon)
            if results["openweather"]:
                print("✅OWM", end=" ", flush=True)
                break
        except Exception as e:
            if attempt == retries - 1:
                print(f"❌OWM", end=" ", flush=True)
    
    # 2. Weatherapi
    for attempt in range(retries):
        try:
            results["weatherapi"] = get_weatherapi_data(lat, lon)
            if results["weatherapi"]:
                print("✅WA", end=" ", flush=True)
                break
        except Exception as e:
            if attempt == retries - 1:
                print(f"❌WA", end=" ", flush=True)
    
    # 3. Open-Meteo (más lenta, último)
    for attempt in range(retries):
        try:
            results["openmeteo"] = get_openmeteo_data(lat, lon)
            if results["openmeteo"]:
                print("✅OM\n", end="", flush=True)
                break
        except Exception as e:
            if attempt == retries - 1:
                print(f"❌OM\n", end="", flush=True)
    
    return results

def calculate_day_average(zona_name, lat, lon, day_idx):
    """Calcula promedio de las 3 APIs para un día específico"""
    apis_data = fetch_all_data_for_zone(zona_name, lat, lon)
    
    parsed = {}
    parsed["openmeteo"] = parse_openmeteo(apis_data.get("openmeteo"), day_idx)
    parsed["openweather"] = parse_openweather(apis_data.get("openweather"), day_idx)
    parsed["weatherapi"] = parse_weatherapi(apis_data.get("weatherapi"), day_idx)
    
    # Filtrar datos válidos
    valid_data = {k: v for k, v in parsed.items() if v is not None}
    
    if not valid_data:
        return None
    
    # Calcular promedios
    winds = [v["wind"] for v in valid_data.values()]
    temps = [v["temp"] for v in valid_data.values()]
    
    avg_wind = statistics.mean(winds)
    avg_temp = statistics.mean(temps)
    
    # Confianza = cuántas APIs coinciden (de 1-3)
    confidence = len(valid_data) / 3 * 100
    
    return {
        "wind": avg_wind,
        "temp": avg_temp,
        "confidence": confidence,
        "sources": len(valid_data)
    }

def calculate_score(wind_knots):
    """Calcula puntuación para offshore (0-10)"""
    if wind_knots > 10:
        return 2, "🔴 PELIGROSO"
    elif wind_knots > 7:
        return 4, "🟠 REGULAR"
    elif wind_knots > 5:
        return 7, "🟡 BUENO"
    else:
        return 10, "🟢 EXCELENTE"

# ==================== REPORTE ====================

def generate_report():
    """Genera reporte de 3 días"""
    now = datetime.now()
    dias = {}
    
    print("\n📊 Consultando 3 APIs para 15 zonas (secuencial)...\n")
    
    # Calcular para 3 días
    for day_idx in range(3):
        día_fecha = now + timedelta(days=day_idx)
        dias[day_idx] = {
            "fecha": día_fecha.strftime("%d/%m"),
            "nombre_dia": ["HOY", "MAÑANA", "PASADO MAÑANA"][day_idx],
            "zonas": []
        }
    
    # Para cada zona y cada día
    zona_count = 0
    for zona_name, (lat, lon) in ZONAS.items():
        zona_count += 1
        print(f"[{zona_count}/15]", end=" ")
        for day_idx in range(3):
            data = calculate_day_average(zona_name, lat, lon, day_idx)
            if data:
                score, rating = calculate_score(data["wind"])
                dias[day_idx]["zonas"].append({
                    "nombre": zona_name,
                    "wind": data["wind"],
                    "temp": data["temp"],
                    "score": score,
                    "rating": rating,
                    "confidence": data["confidence"],
                    "sources": data["sources"]
                })
    
    print("\n✅ Consultas completadas!\n")
    
    # Ordenar zonas por score (mejores primero)
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
    msg += f"🔗 Media de 3 APIs: Open-Meteo + OpenWeatherMap + Weatherapi\n"
    msg += "═" * 50 + "\n\n"
    
    for day_idx in range(3):
        day_info = dias[day_idx]
        msg += f"📌 {day_info['nombre_dia']} {day_info['fecha']}\n"
        
        if day_info["zonas"]:
            # Top 3 zonas
            for i, zona in enumerate(day_info["zonas"][:3]):
                msg += f"  {i+1}. {zona['nombre']}\n"
                msg += f"     Viento: {zona['wind']:.1f} kn | Temp: {zona['temp']:.0f}°C | {zona['rating']}\n"
                msg += f"     Confianza: {zona['confidence']:.0f}% ({zona['sources']}/3 APIs)\n"
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
    else:
        msg += f"🎯 MEJOR DÍA: ⚠️ Sin datos suficientes\n"
    
    msg += "\n💡 CONSEJOS:\n"
    msg += "   • Consulta SIEMPRE las condiciones locales antes de salir\n"
    msg += "   • Llevar: Traje neopreno 3-5mm, casco, GPS, silbato\n"
    msg += "   • NUNCA salir solo en offshore\n"
    msg += "   • Avisa a alguien tu ruta y hora de retorno\n"
    msg += f"🔗 Fuente: Open-Meteo + OpenWeatherMap + Weatherapi\n"
    
    return msg

# ==================== TELEGRAM ====================

def send_to_telegram(message):
    """Envía mensaje a Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
        r = requests.post(url, json=data, timeout=10)
        
        if r.status_code == 200:
            print("✅ Mensaje enviado a Telegram")
        else:
            print(f"❌ Error Telegram: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")

# ==================== MAIN ====================

if __name__ == "__main__":
    print("🚀 Iniciando bot multi-API...\n")
    
    # Verificar credenciales
    if not TOKEN or not CHAT_ID:
        print("❌ Error: TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no configurados")
        exit(1)
    
    # Generar reporte
    print("📊 Generando reporte...")
    report = generate_report()
    
    # Mostrar en consola
    print(report)
    
    # Enviar a Telegram
    print("\n📤 Enviando a Telegram...")
    send_to_telegram(report)
    
    print("✅ ¡Bot completado!")
