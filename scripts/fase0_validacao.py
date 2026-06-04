"""
Fase 0 — Validação da API-Football free tier para seleções nacionais.

Roda uma vez. Gasta ~25 requests dos 100/dia disponíveis.
Resultado: saber exatamente quais dados o projeto pode contar como disponíveis.

Uso:
    python scripts/fase0_validacao.py
"""

import os
import json
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Pausa entre requests para não bater no rate limit por minuto
PAUSE = 1.5

resultados = []
requests_usados = 0


def req(endpoint: str, params: dict = None) -> dict | None:
    global requests_usados
    url = f"{BASE_URL}{endpoint}"
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        requests_usados += 1
        time.sleep(PAUSE)
        if r.status_code != 200:
            return None
        data = r.json()
        # API-Football retorna errors mesmo com 200
        if data.get("errors"):
            return None
        return data
    except Exception:
        return None


def log(status: str, item: str, detalhe: str = ""):
    simbolo = "[OK]" if status == "ok" else ("[!!]" if status == "parcial" else "[XX]")
    linha = f"  {simbolo} {item}"
    if detalhe:
        linha += f" -- {detalhe}"
    print(linha)
    resultados.append({"status": status, "item": item, "detalhe": detalhe})


def checar_credenciais():
    print("\n[1/7] Credenciais e cota do dia")
    data = req("/status")
    if not data:
        log("erro", "Autenticação falhou — verifique API_FOOTBALL_KEY no .env")
        return False
    info = data.get("response", {})
    conta = info.get("account", {})
    sub = info.get("subscription", {})
    requests_info = info.get("requests", {})
    print(f"       Conta: {conta.get('email', '?')}")
    print(f"       Plano: {sub.get('plan', '?')}")
    usados_hoje = requests_info.get('current', '?')
    limite = requests_info.get('limit_day', '?')
    print(f"       Requests hoje: {usados_hoje} / {limite}")
    log("ok", "Autenticação OK", f"{usados_hoje}/{limite} requests usados hoje")
    return True


def checar_copa_2026():
    print("\n[2/7] Copa do Mundo 2026 — fixtures")
    data = req("/fixtures", {"league": 1, "season": 2026})
    if not data:
        log("erro", "Copa 2026 — sem resposta")
        return None
    fixtures = data.get("response", [])
    if not fixtures:
        log("erro", "Copa 2026 — nenhum fixture retornado (temporada pode não estar disponível no free tier)")
        return None
    log("ok", f"Copa 2026 — {len(fixtures)} partidas disponíveis")
    # Retornar alguns IDs para testar stats depois
    ids = [f["fixture"]["id"] for f in fixtures[:3]]
    return ids


def checar_copa_2022():
    print("\n[3/7] Copa do Mundo 2022 — fixtures e estatísticas")
    data = req("/fixtures", {"league": 1, "season": 2022})
    if not data:
        log("erro", "Copa 2022 — sem resposta")
        return None
    fixtures = data.get("response", [])
    if not fixtures:
        log("erro", "Copa 2022 — nenhum fixture retornado")
        return None
    log("ok", f"Copa 2022 — {len(fixtures)} partidas disponíveis")

    # Pegar ID de uma partida com resultado para testar stats
    jogo_com_resultado = next(
        (f for f in fixtures if f["fixture"]["status"]["short"] == "FT"),
        fixtures[0]
    )
    fixture_id = jogo_com_resultado["fixture"]["id"]
    home = jogo_com_resultado["teams"]["home"]["name"]
    away = jogo_com_resultado["teams"]["away"]["name"]
    print(f"       Testando stats de: {home} × {away} (id={fixture_id})")

    stats_data = req("/fixtures/statistics", {"fixture": fixture_id})
    if not stats_data:
        log("erro", "Estatísticas de partida — endpoint não retornou dados")
        return fixture_id

    stats = stats_data.get("response", [])
    if not stats:
        log("parcial", "Estatísticas de partida — resposta vazia para esta partida")
        return fixture_id

    # Mapear quais tipos de stat estão presentes
    tipos_presentes = set()
    for team_stats in stats:
        for s in team_stats.get("statistics", []):
            if s.get("value") is not None:
                tipos_presentes.add(s["type"])

    campos_desejados = {
        "Corner Kicks": "escanteios",
        "Total Shots": "chutes totais",
        "Shots on Goal": "chutes no alvo",
        "Yellow Cards": "cartões amarelos",
        "Red Cards": "cartões vermelhos",
        "Fouls": "faltas",
        "Ball Possession": "posse",
        "expected_goals": "xG",
    }

    for api_nome, pt_nome in campos_desejados.items():
        if api_nome in tipos_presentes:
            log("ok", f"Copa 2022 stats — {pt_nome} disponível")
        else:
            log("erro", f"Copa 2022 stats — {pt_nome} ausente")

    return fixture_id


def checar_eliminatorias():
    print("\n[4/7] Eliminatórias para Copa 2026")
    # IDs das eliminatórias por confederação (v3 API-Football)
    eliminatorias = [
        (29, 2025, "CONMEBOL Eliminatórias"),
        (32, 2024, "UEFA Eliminatórias"),
        (30, 2024, "CONCACAF Eliminatórias"),
        (29, 2024, "CAF (tentativa)"),
    ]
    ids_disponiveis = []
    for league_id, season, nome in eliminatorias:
        data = req("/fixtures", {"league": league_id, "season": season, "last": 5})
        if not data or not data.get("response"):
            log("erro", f"{nome} (league={league_id}, season={season}) — sem dados")
        else:
            qtd = len(data["response"])
            log("ok", f"{nome} — {qtd} partidas recentes disponíveis")
            # Pegar IDs com resultado para testar stats
            com_resultado = [
                f["fixture"]["id"]
                for f in data["response"]
                if f["fixture"]["status"]["short"] == "FT"
            ]
            ids_disponiveis.extend(com_resultado[:1])
    return ids_disponiveis


def checar_stats_eliminatorias(fixture_ids: list[int]):
    print("\n[5/7] Estatísticas das Eliminatórias")
    if not fixture_ids:
        log("erro", "Nenhum fixture de eliminatórias para testar stats")
        return
    fixture_id = fixture_ids[0]
    stats_data = req("/fixtures/statistics", {"fixture": fixture_id})
    if not stats_data or not stats_data.get("response"):
        log("erro", f"Eliminatórias stats (fixture={fixture_id}) — sem dados")
        return
    stats = stats_data["response"]
    tipos = {s["type"] for t in stats for s in t.get("statistics", []) if s.get("value") is not None}
    campos_chave = ["Corner Kicks", "Total Shots", "Yellow Cards", "Fouls"]
    for c in campos_chave:
        if c in tipos:
            log("ok", f"Eliminatórias stats — {c} presente")
        else:
            log("parcial", f"Eliminatórias stats — {c} ausente (fixture={fixture_id})")


def checar_amistosos():
    print("\n[6/7] Amistosos internacionais")
    # League 10 = International — amistosos
    data = req("/fixtures", {"league": 10, "season": 2025, "last": 5})
    if not data or not data.get("response"):
        log("erro", "Amistosos internacionais 2025 — sem fixtures")
        return
    fixtures = data["response"]
    log("ok", f"Amistosos — {len(fixtures)} partidas recentes disponíveis")

    com_resultado = [
        f["fixture"]["id"]
        for f in fixtures
        if f["fixture"]["status"]["short"] == "FT"
    ]
    if not com_resultado:
        log("parcial", "Amistosos — nenhuma partida finalizada no batch retornado")
        return

    stats_data = req("/fixtures/statistics", {"fixture": com_resultado[0]})
    if not stats_data or not stats_data.get("response"):
        log("parcial", f"Amistosos stats — sem dados (fixture={com_resultado[0]})")
        return
    stats = stats_data["response"]
    tipos = {s["type"] for t in stats for s in t.get("statistics", []) if s.get("value") is not None}
    if "Corner Kicks" in tipos or "Total Shots" in tipos:
        log("ok", "Amistosos stats — estatísticas de partida presentes")
    else:
        log("parcial", "Amistosos stats — estatísticas ausentes ou incompletas (cobertura inconsistente, como documentado no PRD)")


def checar_club_elo():
    print("\n[7/7] Club Elo — rating prior de seleções nacionais")
    try:
        r = requests.get("http://api.clubelo.com/BRA", timeout=10)
        time.sleep(PAUSE)
        if r.status_code == 200 and r.text.strip():
            linhas = r.text.strip().split("\n")
            ultimo = linhas[-1].split(",")
            elo_brasil = float(ultimo[4]) if len(ultimo) > 4 else None
            if elo_brasil:
                log("ok", f"Club Elo — disponível. Elo Brasil atual: {elo_brasil:.0f}")
            else:
                log("parcial", "Club Elo — resposta recebida mas parsing falhou")
        else:
            log("erro", "Club Elo — sem resposta")
    except Exception as e:
        log("erro", f"Club Elo — erro: {e}")


def imprimir_resumo():
    print("\n" + "="*60)
    print("RESUMO DA FASE 0")
    print("="*60)

    ok = [r for r in resultados if r["status"] == "ok"]
    parcial = [r for r in resultados if r["status"] == "parcial"]
    erros = [r for r in resultados if r["status"] == "erro"]

    print(f"\n[OK] OK:      {len(ok)}")
    print(f"[!!] Parcial: {len(parcial)}")
    print(f"[XX] Erro:    {len(erros)}")
    print(f"\nRequests usados nesta execução: {requests_usados}")

    if erros:
        print("\nItens com ERRO (atenção para atualizar DECISIONS.md):")
        for e in erros:
            print(f"  [XX] {e['item']}: {e['detalhe']}")

    if parcial:
        print("\nItens PARCIAIS:")
        for p in parcial:
            print(f"  [!!] {p['item']}: {p['detalhe']}")

    # Salvar resultado em JSON para referência
    Path("dados").mkdir(exist_ok=True)
    output_path = Path("dados/fase0_resultado.json")
    output_path.write_text(
        json.dumps({"requests_usados": requests_usados, "resultados": resultados}, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\nResultado salvo em: {output_path}")
    print("\nPróximo passo: atualizar docs/DECISIONS.md Decisões 1 e 2 com base nestes resultados.")


if __name__ == "__main__":
    print("Copa Analyst — Fase 0: Validação de Dados")
    print(f"API Key: {'configurada' if API_KEY else '❌ NÃO ENCONTRADA — configure .env'}")

    if not API_KEY:
        exit(1)

    ok = checar_credenciais()
    if not ok:
        print("\n❌ Autenticação falhou. Verifique API_FOOTBALL_KEY no .env e tente de novo.")
        exit(1)

    ids_copa_2026 = checar_copa_2026()
    checar_copa_2022()
    ids_elim = checar_eliminatorias()
    checar_stats_eliminatorias(ids_elim)
    checar_amistosos()
    checar_club_elo()
    imprimir_resumo()
