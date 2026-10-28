import json, os, requests
from datetime import datetime

# Función para obtener los precios P2P de Binance (General, Zinli, Wally)
def fetch_binance_p2p(fiat="VES", pay_type=None):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {"Content-Type": "application/json"}
    
    # Configuración de la petición
    payload = {
        "page": 1, "rows": 5, "payTypes": [pay_type] if pay_type else [],
        "asset": "USDT", "fiat": fiat, "tradeType": "SELL"
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if data:
            # Calculamos el promedio de los primeros 5 anuncios
            precios = [float(adv["adv"]["price"]) for adv in data]
            return round(sum(precios) / len(precios), 2)
    except Exception as e:
        print(f"Error Binance {pay_type}: {e}")
    return None

# Función para obtener precios de CriptoYa (Bybit, OKX, COP)
def fetch_criptoya(exchange, fiat="VES"):
    url = f"https://criptoya.com/api/{exchange}/USDT/{fiat}/1"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return {"ask": data.get("ask"), "bid": data.get("bid")}
    except Exception as e:
        print(f"Error CriptoYa {exchange}: {e}")
        return None

def main():
    os.makedirs("data", exist_ok=True)
    precios = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "binance_ves": fetch_binance_p2p("VES"),
        "binance_zinli": fetch_binance_p2p("VES", "Zinli"),
        "binance_wally": fetch_binance_p2p("VES", "Wally"),
        "bybit_ves": fetch_criptoya("bybitp2p", "VES"),
        "okx_ves": fetch_criptoya("okexp2p", "VES"),
        "binance_cop": fetch_binance_p2p("COP")
    }

    # Guardar en un archivo JSON
    with open("data/precios.json", "w", encoding="utf-8") as f:
        json.dump(precios, f, ensure_ascii=False, indent=2)
    
    print("Datos guardados:", precios)

if _name_ == "_main_":
    main()
