import json, os, requests
from datetime import datetime

def fetch_binance_p2p(fiat="VES", pay_type=None):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {"Content-Type": "application/json"}
    payload = {
        "page": 1, "rows": 5, "payTypes": [pay_type] if pay_type else [],
        "asset": "USDT", "fiat": fiat, "tradeType": "SELL"
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if data:
            precios = [float(adv["adv"]["price"]) for adv in data]
            return round(sum(precios) / len(precios), 2)
    except Exception as e:
        print(f"Error Binance {pay_type}: {e}")
    return None

def fetch_criptoya(exchange, fiat="VES"):
    url = f"https://criptoya.com/api/{exchange}/USDT/{fiat}/1"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        # Algunos exchanges usan 'ask' y 'bid', otros 'pregunta' y 'venta'
        ask = data.get("ask") or data.get("pregunta")
        bid = data.get("bid") or data.get("venta")
        return {"ask": ask, "bid": bid}
    except Exception as e:
        print(f"Error CriptoYa {exchange}: {e}")
        return None

def main():
    os.makedirs("data", exist_ok=True)
    
    # Leer el historial existente si ya existe
    historial = []
    if os.path.exists("data/precios.json"):
        try:
            with open("data/precios.json", "r", encoding="utf-8") as f:
                historial = json.load(f)
                # Si por alguna razón el archivo no es una lista, lo reiniciamos
                if not isinstance(historial, list):
                    historial = []
        except:
            historial = []

    # Crear el nuevo registro
    nuevo_precio = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "binance_ves": fetch_binance_p2p("VES"),
        "binance_zinli": fetch_binance_p2p("VES", "Zinli"),
        "binance_wally": fetch_binance_p2p("VES", "Wally"),
        "bybit_ves": fetch_criptoya("bybitp2p", "VES"),
        "okx_ves": fetch_criptoya("okexp2p", "VES"),
        "binance_cop": fetch_binance_p2p("COP")
    }

    # Añadir al historial y mantener solo los últimos 500 registros (para que no pese mucho)
    historial.append(nuevo_precio)
    historial = historial[-500:]

    # Guardar en el archivo JSON
    with open("data/precios.json", "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)
    
    print("Historial guardado. Total registros:", len(historial))

if _name_ == "_main_":
    main()
