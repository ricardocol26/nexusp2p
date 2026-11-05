#!/usr/bin/env python3
"""Radar P2P · ingesta de tasas reales vía Cotizave + pronóstico estadístico."""
import json, os, math, time, statistics, sys
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API   = "https://api.cotizave.com/v1/fx/rates"
KEY   = (os.environ.get("COTIZAVE_API_KEY") or "").strip()
VE    = timezone(timedelta(hours=-4))
DATA  = "data"
HIST  = os.path.join(DATA, "historial.json")
OUT   = os.path.join(DATA, "precios.json")
MERCADOS = ("binance", "bybit", "okx")
MIN_CUOTA = 25
MAX_DIAS  = 45

if not KEY:
    sys.exit("falta COTIZAVE_API_KEY")

def pedir():
    for intento in range(3):
        req = Request(API, headers={
            "X-API-Key": KEY, "Accept": "application/json",
            "User-Agent": "nexusp2p-radar/1.0",
        })
        try:
            with urlopen(req, timeout=25) as r:
                resto = r.headers.get("X-RateLimit-Remaining")
                return json.loads(r.read().decode()), resto
        except HTTPError as e:
            if e.code == 429:
                time.sleep(min(int(e.headers.get("Retry-After") or 30), 60)); continue
            if e.code in (401, 402, 403):
                sys.exit(f"acceso rechazado {e.code}: {e.read()[:200]}")
            if 500 <= e.code < 600:
                time.sleep(8); continue
            raise
        except URLError:
            time.sleep(6)
    sys.exit("sin respuesta de Cotizave")

def normalizar(payload):
    filas = payload.get("rates") or payload.get("data") or []
    salida = {}
    for f in filas:
        if (f.get("type") or "").lower() not in ("p2p", "crypto_p2p"):
            continue
        m = (f.get("market") or f.get("id") or "").lower().replace("ve-", "").replace("ve_", "")
        if m not in MERCADOS:
            continue
        ask, bid = f.get("ask"), f.get("bid")
        if ask is None and bid is None:
            continue
        salida[m] = {"ask": ask, "bid": bid, "ts": f.get("updated_at")}
    return salida

def rsi(v, n=14):
    if len(v) < n + 1: return 50.0
    g = p = 0.0
    for i in range(-n, 0):
        d = v[i] - v[i - 1]
        g += max(d, 0); p += max(-d, 0)
    if p == 0: return 100.0
    return 100 - 100 / (1 + (g / n) / (p / n))

def bandas(v, n=20, k=2.0):
    w = v[-n:]
    if len(w) < 6:
        m = v[-1]; s = max(m * 0.002, 0.01)
    else:
        m = statistics.fmean(w); s = statistics.pstdev(w) or v[-1] * 0.001
    return m, m + k * s, m - k * s, s

def pendiente(v):
    n = len(v)
    if n < 2: return 0.0
    xs = list(range(n)); mx = (n - 1) / 2; my = statistics.fmean(v)
    num = sum((xs[i] - mx) * (v[i] - my) for i in range(n))
    den = sum((x - mx) ** 2 for x in xs) or 1
    return num / den

def pronostico(v):
    _, _, _, s = bandas(v)
    ult = v[-1]
    pend = pendiente(v[-12:])
    r = rsi(v)
    t0 = datetime.now(VE)
    serie = []
    for h in range(1, 18):
        centro = ult + pend * h * (0.88 ** h)
        amp = s * math.sqrt(h / 4.0) * (1 + h / 40)
        serie.append({
            "fecha": (t0 + timedelta(hours=h)).isoformat(timespec="seconds"),
            "central": round(centro, 2),
            "techo": round(min(centro + amp, ult * 1.035), 2),
            "piso": round(max(centro - amp, ult * 0.965), 2),
        })
    conf = max(0, min(100, round(100 - (s / ult * 100) * 60 - abs(r - 50) * 1.1)))
    return {
        "serie": serie,
        "techo": max(p["techo"] for p in serie),
        "piso": min(p["piso"] for p in serie),
        "rsi": round(r, 1), "volatilidad": round(s, 2), "confianza": conf,
    }

def niveles(v, ventana=10):
    techos, pisos = [], []
    for i in range(ventana, len(v) - ventana):
        w = v[i - ventana:i + ventana + 1]
        if v[i] == max(w): techos.append(round(v[i], 2))
        if v[i] == min(w): pisos.append(round(v[i], 2))
    return {"resistencias": sorted(set(techos))[-4:], "soportes": sorted(set(pisos))[:4]}

# NUEVA FUNCIÓN: Pronóstico a largo plazo (Día siguiente y Semana)
def proyeccion_largo_plazo(historial):
    dias = {}
    # Agrupamos los datos por día
    for h in historial:
        if not h.get("binance_ves"): continue
        dia = h["fecha"][:10]
        if dia not in dias:
            dias[dia] = {"techo": h["binance_ves"], "piso": h["binance_ves"]}
        else:
            dias[dia]["techo"] = max(dias[dia]["techo"], h["binance_ves"])
            dias[dia]["piso"] = min(dias[dia]["piso"], h["binance_ves"])
    
    # Si no hay suficientes días de datos, devolvemos null
    if len(dias) < 2:
        return {"mañana_techo": None, "mañana_piso": None, "semana_techo": None, "semana_piso": None}
        
    techos = [dias[d]["techo"] for d in dias]
    pisos = [dias[d]["piso"] for d in dias]
    
    # Calculamos promedios históricos para proyectar
    prom_techo = statistics.fmean(techos)
    prom_piso = statistics.fmean(pisos)
    
    return {
        "mañana_techo": round(prom_techo * 1.005, 2),
        "mañana_piso": round(prom_piso * 0.995, 2),
        "semana_techo": round(max(techos) * 1.01, 2),
        "semana_piso": round(min(pisos) * 0.99, 2)
    }

def main():
    payload, resto = pedir()
    if resto is not None and int(resto) < MIN_CUOTA:
        print(f"cuota baja ({resto}), se omite esta corrida"); return

    tasas = normalizar(payload)
    bn = tasas.get("binance")
    if not bn or bn.get("ask") is None:
        sys.exit("sin tasa de Binance en la respuesta")

    ahora = datetime.now(VE)
    punto = {
        "fecha": ahora.isoformat(timespec="seconds"),
        "binance_ves": bn["ask"],
        "binance_compra": bn.get("bid"),
        "bybit_ves": tasas.get("bybit"),
        "okx_ves": tasas.get("okx"),
    }

    historial = []
    if os.path.exists(HIST):
        with open(HIST, encoding="utf-8") as f:
            historial = json.load(f)
    historial.append(punto)

    corte = (ahora - timedelta(days=MAX_DIAS)).isoformat(timespec="seconds")
    historial = [h for h in historial if h["fecha"] >= corte]

    precios = [h["binance_ves"] for h in historial if h.get("binance_ves")]
    hoy = ahora.date().isoformat()
    delDia = [h["binance_ves"] for h in historial if h["fecha"].startswith(hoy) and h.get("binance_ves")]

    proy = pronostico(precios[-288:] if len(precios) >= 30 else precios)
    proy_largo = proyeccion_largo_plazo(historial)
    
    techoDia, pisoDia = max(delDia or precios), min(delDia or precios)
    var = ((delDia[-1] - delDia[0]) / delDia[0] * 100) if len(delDia) > 2 else 0.0

    os.makedirs(DATA, exist_ok=True)
    with open(HIST, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False)

    salida = {
        "actualizado": punto["fecha"],
        "fuente": "cotizave",
        "puntos": [h for h in historial if h["fecha"].startswith(hoy)],
        "metricas": {
            "techo_dia": techoDia, "piso_dia": pisoDia,
            "spread_max": round(techoDia - pisoDia, 2),
            "spread_pct": round((techoDia - pisoDia) / pisoDia * 100, 2),
            "rsi": proy["rsi"], "volatilidad": proy["volatilidad"],
            "confianza": proy["confianza"],
            "mercado": ("Subiendo" if var > 0.15 else "Bajando lento" if var < -0.15 else "Lateral"),
            "variacion_pct": round(var, 2),
        },
        "niveles": niveles(precios[-120:]),
        "pronostico": proy,
        "pronostico_largo": proy_largo # <-- AQUÍ ESTÁ LO NUEVO
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    print(f"ok {punto['binance_ves']} · cuota restante {resto}")

if __name__ == '__main__':
    main()
