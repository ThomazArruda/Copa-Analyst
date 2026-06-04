"""
Fase 0 - Parte 2: descobrir league IDs corretos para eliminatórias,
confirmar Copa 2026, e corrigir Club Elo.

Usa ~15 requests.
"""

import os
import json
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
        print(f"  HTTP {r.status_code} para {endpoint} {params}")
        return None
    data = r.json()
    if data.get("errors"):
        print(f"  Erro da API: {data['errors']}")
        return None
    return data


# --- 1. Buscar leagues com "World Cup" no nome ---
print("\n[A] Buscando leagues com 'World Cup'")
data = req("/leagues", {"search": "World Cup"})
if data:
    for lg in data.get("response", []):
        l = lg["league"]
        c = lg.get("country", {})
        seasons = [s["year"] for s in lg.get("seasons", [])]
        print(f"  id={l['id']:5d}  nome={l['name']:<40s}  pais={c.get('name','?'):<15s}  seasons={seasons[-5:]}")


# --- 2. Buscar leagues com "Qualification" ---
print("\n[B] Buscando leagues com 'Qualification'")
data = req("/leagues", {"search": "Qualification"})
if data:
    for lg in data.get("response", []):
        l = lg["league"]
        c = lg.get("country", {})
        seasons = [s["year"] for s in lg.get("seasons", [])]
        print(f"  id={l['id']:5d}  nome={l['name']:<40s}  pais={c.get('name','?'):<15s}  seasons={seasons[-3:]}")


# --- 3. Fixtures Copa 2026 com parâmetros alternativos ---
print("\n[C] Copa 2026 -- tentativas alternativas")
for params in [
    {"league": 1, "season": 2026},
    {"league": 1, "season": 2025},
]:
    data = req("/fixtures", params)
    count = len(data.get("response", [])) if data else 0
    print(f"  league=1 season={params['season']} -> {count} fixtures")


# --- 4. Testar cartao vermelho em outro jogo da Copa 2022 ---
print("\n[D] Testando stat 'cartao vermelho' em jogos Copa 2022 especificos")
# Buscar jogos que tiveram cartao vermelho (pela API, filtrar por "red")
for fixture_id in [855769, 855770, 855771]:  # alguns IDs aleatórios da Copa 2022
    data = req("/fixtures/statistics", {"fixture": fixture_id})
    if not data or not data.get("response"):
        print(f"  fixture={fixture_id}: sem stats")
        continue
    tipos = {s["type"]: s["value"] for t in data["response"] for s in t.get("statistics", [])}
    red = tipos.get("Red Cards")
    yellow = tipos.get("Yellow Cards")
    print(f"  fixture={fixture_id}: yellow={yellow}, red={red}")


# --- 5. Club Elo --- corrigido
print("\n[E] Club Elo -- corrigido (pular header)")
selecoes = ["BRA", "ARG", "FRA", "ENG", "GER"]
for sel in selecoes:
    r = requests.get(f"http://api.clubelo.com/{sel}", timeout=10)
    time.sleep(0.5)
    if r.status_code != 200:
        print(f"  {sel}: HTTP {r.status_code}")
        continue
    linhas = [l for l in r.text.strip().split("\n") if not l.startswith("Club")]
    if not linhas:
        print(f"  {sel}: sem dados")
        continue
    ultimo = linhas[-1].split(",")
    try:
        elo = float(ultimo[4])
        data_ref = ultimo[5] if len(ultimo) > 5 else "?"
        print(f"  {sel}: Elo={elo:.0f}  (referencia={data_ref})")
    except (ValueError, IndexError) as e:
        print(f"  {sel}: erro parse -- {e} -- linha: {linhas[-1][:80]}")


# --- 6. Testar amistosos com league 10, temporadas alternativas ---
print("\n[F] Amistosos internacionais -- league=10, varias temporadas")
for season in [2026, 2025, 2024]:
    data = req("/fixtures", {"league": 10, "season": season, "last": 5})
    count = len(data.get("response", [])) if data else 0
    print(f"  league=10 season={season} -> {count} fixtures")


print(f"\nRequests usados nesta parte: {requests_usados}")
