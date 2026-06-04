"""
Fase 0 - Parte 3: testar eliminatórias com IDs corretos e seasons acessíveis,
amistosos 2024 sem parâmetro "last", e Club Elo com parse corrigido.

Usa ~12 requests.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
PAUSE = 1.5
requests_usados = 0


def req(endpoint, params=None):
    global requests_usados
    r = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params, timeout=10)
    requests_usados += 1
    time.sleep(PAUSE)
    if r.status_code != 200:
        return None
    data = r.json()
    if data.get("errors"):
        print(f"  BLOQUEADO: {list(data['errors'].values())[0]}")
        return None
    return data


# --- 1. Eliminatórias: IDs corretos, seasons que devem funcionar ---
print("\n[A] Eliminatorias -- IDs corretos, seasons 2022-2024")
eliminatorias = [
    (34, 2026, "CONMEBOL (South America)"),
    (34, 2022, "CONMEBOL (South America)"),
    (32, 2024, "UEFA"),
    (31, 2026, "CONCACAF"),
    (31, 2022, "CONCACAF"),
    (30, 2026, "Asia"),
    (30, 2022, "Asia"),
    (29, 2022, "Africa"),
]
ids_com_resultado = []
for league_id, season, nome in eliminatorias:
    data = req("/fixtures", {"league": league_id, "season": season})
    if not data:
        print(f"  [XX] {nome} league={league_id} season={season}")
        continue
    fixtures = data.get("response", [])
    finalizados = [f for f in fixtures if f["fixture"]["status"]["short"] == "FT"]
    print(f"  [OK] {nome} league={league_id} season={season} -> {len(fixtures)} fixtures, {len(finalizados)} finalizados")
    if finalizados:
        ids_com_resultado.append(finalizados[0]["fixture"]["id"])


# --- 2. Stats de uma eliminatória ---
print("\n[B] Estatisticas de eliminatoria (primeiro fixture disponivel)")
if ids_com_resultado:
    fid = ids_com_resultado[0]
    data = req("/fixtures/statistics", {"fixture": fid})
    if data and data.get("response"):
        stats = data["response"]
        tipos = {}
        for team in stats:
            for s in team.get("statistics", []):
                if s.get("value") is not None:
                    tipos[s["type"]] = s["value"]
        campos = ["Corner Kicks", "Total Shots", "Shots on Goal", "Yellow Cards", "Red Cards", "Fouls", "Ball Possession"]
        for c in campos:
            val = tipos.get(c)
            status = "[OK]" if val is not None else "[XX]"
            print(f"  {status} {c}: {val}")
    else:
        print(f"  [XX] Sem stats para fixture={fid}")
else:
    print("  [XX] Nenhum fixture disponivel para testar")


# --- 3. Amistosos 2024 sem parametro "last" ---
print("\n[C] Amistosos internacionais -- league=10, season=2024, sem 'last'")
data = req("/fixtures", {"league": 10, "season": 2024})
if data:
    fixtures = data.get("response", [])
    finalizados = [f for f in fixtures if f["fixture"]["status"]["short"] == "FT"]
    print(f"  [OK] {len(fixtures)} fixtures, {len(finalizados)} finalizados")
    if finalizados:
        fid = finalizados[0]["fixture"]["id"]
        home = finalizados[0]["teams"]["home"]["name"]
        away = finalizados[0]["teams"]["away"]["name"]
        print(f"  Testando stats: {home} x {away} (id={fid})")
        stats_data = req("/fixtures/statistics", {"fixture": fid})
        if stats_data and stats_data.get("response"):
            tipos = {s["type"]: s["value"]
                     for t in stats_data["response"]
                     for s in t.get("statistics", [])
                     if s.get("value") is not None}
            for c in ["Corner Kicks", "Total Shots", "Yellow Cards", "Fouls"]:
                status = "[OK]" if c in tipos else "[XX]"
                print(f"  {status} {c}")
        else:
            print("  [XX] Sem stats para amistoso")
else:
    print("  [XX] Sem fixtures")


# --- 4. Club Elo -- parse corrigido (filtrar linhas que comecam com digito) ---
print("\n[D] Club Elo -- parse corrigido")
selecoes = {
    "BRA": "Brasil", "ARG": "Argentina", "FRA": "Franca",
    "ENG": "Inglaterra", "GER": "Alemanha", "ESP": "Espanha",
    "POR": "Portugal", "NED": "Holanda", "ITA": "Italia", "URU": "Uruguai"
}
elos = {}
for codigo, nome in selecoes.items():
    r = requests.get(f"http://api.clubelo.com/{codigo}", timeout=10)
    time.sleep(0.5)
    if r.status_code != 200:
        print(f"  [XX] {nome}: HTTP {r.status_code}")
        continue
    linhas = [l for l in r.text.strip().split("\n") if l and l[0].isdigit()]
    if not linhas:
        print(f"  [XX] {nome}: sem linhas com dados")
        continue
    ultimo = linhas[-1].split(",")
    try:
        elo = float(ultimo[4])
        data_ref = ultimo[6] if len(ultimo) > 6 else "?"
        elos[codigo] = elo
        print(f"  [OK] {nome} ({codigo}): Elo={elo:.0f}  ate={data_ref.strip()}")
    except (ValueError, IndexError) as e:
        print(f"  [XX] {nome}: erro -- {e}")

if elos:
    ranking = sorted(elos.items(), key=lambda x: x[1], reverse=True)
    print(f"\n  Ranking amostral: {' > '.join(f'{c}({v:.0f})' for c, v in ranking)}")


print(f"\nRequests usados nesta parte: {requests_usados}")
print("Total estimado do dia: ~30 requests")
