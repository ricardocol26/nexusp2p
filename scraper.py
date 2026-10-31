import json, os, requests
from datetime import datetime

# --- CONFIGURACIÓN DE FILTROS ---
MIN_LIQUIDEZ = 50.0  # Solo ofertas con más de 50 USDT disponibles

# Lista maestra de bancos de Venezuela (en minúsculas)
BANCOS_VENEZUELA = [
    "banesco", "mercantil", "provincial", "venezuela", 
    "banca amiga", "bnc", "banplus", "bancaribe", "exterior", "plaza"
]

def fetch_binance_p2p(fiat="VES", pay_type=None):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    
    # Disfraz de navegador para evitar bloqueos de Binance
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "/"
    }
    
    # Pedimos 20 anuncios generales para poder filtrar los bancos localmente
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
            
            # 1. Filtro de Liquidez (Ignorar ofertas muy pequeñas)
            if surplus < MIN_LIQUIDEZ:
                continue
                
            # 2. Filtro de Bancos (Solo si estamos buscando VES general)
            if not pay_type:
                metodos = [m["tradeMethodName"].lower() for m in adv["adv"]["tradeMethods"]]
                # Si no acepta ninguno de nuestros bancos, lo saltamos
                if not any(banco in metodos for banco in BANCOS_VENEZUELA):
                    continue
            
            ofertas_validas.append(precio)
                
        if ofertas_validas:
            # Promedio de las 5 mejores ofertas que pasaron los filtros
            mejores = ofertas_validas[:5]
            return round(sum(mejores) / len(mejores), 2)
        else:
            print(f"Advertencia: No hay ofertas válidas para {pay_type or 'Bancos de Venezuela'}")
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
        def main():
    os.makedirs("data", exist_ok=True)
    
    # Leer el historial existente para no borrar los datos anteriores
    historial = []
    if os.path.exists("data/precios.json"):
        try:
            with open("data/precios.json", "r", encoding="utf-8") as f:
                historial = json.load(f)
                if not isinstance(historial, list):
                    historial = []
        except:
            historial = []

    print("Consultando Binance (Todos los bancos + Liquidez) y CriptoYa...")
    nuevo_precio = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "binance_ves": fetch_binance_p2p("VES"), 
        "binance_zinli": fetch_binance_p2p("VES", "Zinli"),
        "binance_wally": fetch_binance_p2p("VES", "Wally"),
        "bybit_ves": fetch_criptoya("bybitp2p", "VES"),
        "okx_ves": fetch_criptoya("okexp2p", "VES")
    }

    # Añadir el nuevo precio al historial
    historial.append(nuevo_precio)
    historial = historial[-500:] # Guardar solo los últimos 500 registros

    # Guardar en el archivo JSON
    with open("data/precios.json", "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)
    
    print("Datos guardados exitosamente:", nuevo_precio)

if _name_ == "_main_":
    main()
        print(f"Error CriptoYa {exchange}: {e}")
        return None
