import json, os, requests
from datetime import datetime

MIN_LIQUIDEZ = 50.0

BANCOS_VENEZUELA = [
    "banesco", "mercantil", "provincial", "venezuela", 
    "banca amiga", "bnc", "banplus", "bancaribe", "exterior", "plaza"
]

def fetch_binance_p2p(fiat="VES", pay_type=None):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "/"
    }
    payload = {
        "page": 1, 
        "rows": 20 if not pay_type else 5, 
        "payTypes": [pay_type] if pay_type else [],
        "asset": "USDT", 
        "fiat": fiat, 
        "tradeType": "SELL"
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        
        ofertas_validas = []
        for adv in data:
            precio = float(adv["adv"]["price"])
            surplus = float(adv["adv"]["surplusAmount"])
            
            if surplus < MIN_LIQUIDEZ:
                continue
                
            if not pay_type:
                metodos = [m["tradeMethodName"].lower() for m in adv["adv"]["tradeMethods"]]
                if not any(banco in metodos for banco in BANCOS_VENEZUELA):
                    continue
            
            ofertas_validas.append(precio)
                
        if ofertas_validas:
            mejores = ofertas_validas[:5]
            return round(sum(mejores) / len(mejores), 2)
        else:
            return None
            
    except Exception as e:
        print(f"Error Binance {pay_type}: {e}")
        return None

def fetch_criptoya(exchange, fiat="VES"):
    url = f"https://criptoya.com/api/{exchange}/USDT/{fiat}/1"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        ask = data.get("ask") or data.get("pregunta")
        bid = data.get("bid") or data.get("venta")
        return {"ask": ask, "bid": bid}
    except Exception as e:
        print(f"Error CriptoYa {exchange}: {e}")
        return None

def main():
    os.makedirs("data", exist_ok=True)
    
    historial = []
    if os.path.exists("data/precios.json"):
        try:
            with open("data/precios.json", "r", encoding="utf-8") as f:
                historial = json.load(f)
                if not isinstance(historial, list):
                    historial = []
        except:
            historial = []

    print("Consultando Binance y CriptoYa...")
    nuevo_precio = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "binance_ves": fetch_binance_p2p("VES"), 
        "binance_zinli": fetch_binance_p2p("VES", "Zinli"),
        "binance_wally": fetch_binance_p2p("VES", "Wally"),
        "bybit_ves": fetch_criptoya("bybitp2p", "VES"),
        "okx_ves": fetch_criptoya("okexp2p", "VES")
    }

    historial.append(nuevo_precio)
    historial = historial[-500:]

    with open("data/precios.json", "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)
    
    print("Datos guardados exitosamente:", nuevo_precio)

if __name__ == '__main__':
    main()
