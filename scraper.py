import json, os, requests
from datetime import datetime

# Nueva función que usa CriptoYa para TODOS los exchanges (evita el bloqueo)
def fetch_criptoya(exchange, fiat="VES"):
    url = f"https://criptoya.com/api/{exchange}/USDT/{fiat}/1"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        # CriptoYa devuelve 'ask' (venta) y 'bid' (compra)
        return {
            "ask": data.get("ask") or data.get("pregunta"), 
            "bid": data.get("bid") or data.get("venta")
        }
    except Exception as e:
        print(f"Error CriptoYa {exchange}: {e}")
        return None

def main():
    os.makedirs("data", exist_ok=True)
    
    # Leer historial
    historial = []
    if os.path.exists("data/precios.json"):
        try:
            with open("data/precios.json", "r", encoding="utf-8") as f:
                historial = json.load(f)
                if not isinstance(historial, list):
                    historial = []
        except:
            historial = []

    print("Consultando CriptoYa (Binance, Bybit, OKX)...")
    
    # Usamos 'binancep2p' en lugar de la API directa
    binance_data = fetch_criptoya("binancep2p", "VES")
    
    nuevo_precio = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # Guardamos el ask de Binance como el precio de venta
        "binance_ves": binance_data["ask"] if binance_data else None,
        "binance_zinli": None, # Dejamos Zinli/Wally en pausa para no ser bloqueados
        "binance_wally": None,
        "bybit_ves": fetch_criptoya("bybitp2p", "VES"),
        "okx_ves": fetch_criptoya("okexp2p", "VES")
    }

    historial.append(nuevo_precio)
    historial = historial[-500:]

    with open("data/precios.json", "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)
    
    print("Datos guardados exitosamente:", nuevo_precio)

if _name_ == "_main_":
    main()
