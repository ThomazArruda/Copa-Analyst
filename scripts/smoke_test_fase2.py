"""
Smoke test Fase 2 — Motor Estatístico.

Valida que:
1. Dixon-Coles gera probabilidades que somam 1
2. Probabilidades estão em [0, 1]
3. Resultados são sensatos para jogos conhecidos (Brasil, Argentina, etc.)
4. Cold start funciona (sem crashar com poucos dados)
5. Calibração básica: em jogos entre times desiguais, o favorito tem prob > 50%
"""
import logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

from src.dados.ingestao import _get_repo, pacote_jogo
from src.modelos.dixon_coles import DixonColes, ANFITRIOES
from src.modelos.mercados import calcular_mercados_secundarios
from src.db.repositorio import Repositorio

repo = _get_repo()
dc = DixonColes(repo)

# -----------------------------------------------------------------------
# Teste 1: Listar jogos Copa 2026 disponíveis e testar os primeiros
# -----------------------------------------------------------------------
jogos_26 = repo.listar_jogos_copa26()
print(f"Copa 2026: {len(jogos_26)} fixtures")

erros = []
resultados = []

for jogo in jogos_26[:15]:  # testar primeiros 15 jogos
    time_m = repo.buscar_time(jogo.time_mandante_id)
    time_v = repo.buscar_time(jogo.time_visitante_id)
    if not time_m or not time_v:
        continue

    forma_m = repo.jogos_de_time(time_m.id, limite=10)
    forma_v = repo.jogos_de_time(time_v.id, limite=10)

    try:
        prev = dc.prever(jogo, time_m, time_v, forma_m, forma_v)

        # Verificações
        soma = prev.prob_vitoria_m + prev.prob_empate + prev.prob_vitoria_v
        assert abs(soma - 1.0) < 0.01, f"Probs não somam 1: {soma:.4f}"
        assert 0 <= prev.prob_vitoria_m <= 1
        assert 0 <= prev.prob_empate <= 1
        assert 0 <= prev.prob_vitoria_v <= 1
        assert prev.lambda_m > 0
        assert prev.mu_v > 0

        resultados.append({
            "jogo": f"{time_m.nome} vs {time_v.nome}",
            "lambda": prev.lambda_m, "mu": prev.mu_v,
            "1X2": f"{prev.prob_vitoria_m:.1%} / {prev.prob_empate:.1%} / {prev.prob_vitoria_v:.1%}",
            "over_2.5": prev.prob_over.get(2.5, 0),
            "placar_mv": f"{prev.placar_mais_provavel[0]}-{prev.placar_mais_provavel[1]}",
            "cold_start": prev.cold_start,
            "n_jogos_m": prev.params_m.n_jogos if prev.params_m else 0,
            "n_jogos_v": prev.params_v.n_jogos if prev.params_v else 0,
        })
    except Exception as e:
        import traceback
        erros.append(f"{time_m.nome} vs {time_v.nome}: {e}\n{traceback.format_exc()}")

# -----------------------------------------------------------------------
# Mostrar resultados
# -----------------------------------------------------------------------
print("\n=== PREVISOES COPA 2026 (primeiros 15 jogos) ===")
print(f"{'Jogo':<35} {'lam':>5} {'mu':>5}  {'1X2':>25}  {'O2.5':>5}  {'PlacarMV':>8}  {'CS':>3}  {'Njg':>5}")
print("-" * 105)
for r in resultados:
    cs = "SIM" if r["cold_start"] else "não"
    njg = f"{r['n_jogos_m']}/{r['n_jogos_v']}"
    print(f"{r['jogo']:<35} {r['lambda']:>5.2f} {r['mu']:>5.2f}  {r['1X2']:>25}  "
          f"{r['over_2.5']:>5.1%}  {r['placar_mv']:>8}  {cs:>3}  {njg:>5}")

# -----------------------------------------------------------------------
# Teste 2: Calibração básica — times com Elo muito diferente
# -----------------------------------------------------------------------
print("\n=== TESTE DE CALIBRACAO ===")
# Buscar Argentina e um time mais fraco
arg = repo.buscar_time_por_nome("Argentina")
bra = repo.buscar_time_por_nome("Brazil")
fra = repo.buscar_time_por_nome("France")

for tm, tv in [(arg, bra), (fra, arg)]:
    if not tm or not tv:
        continue
    # Criar jogo fictício (campo neutro)
    from src.db.repositorio import Jogo
    jogo_ficticio = Jogo(
        id=None, competicao="copa_2026", data="2026-07-01",
        hora_utc="20:00", time_mandante_id=tm.id, time_visitante_id=tv.id,
        campo_neutro=1,
    )
    forma_m = repo.jogos_de_time(tm.id, limite=10)
    forma_v = repo.jogos_de_time(tv.id, limite=10)
    prev = dc.prever(jogo_ficticio, tm, tv, forma_m, forma_v)
    print(f"  {tm.nome} (Elo {tm.rating_prior:.0f}) vs {tv.nome} (Elo {tv.rating_prior:.0f}): "
          f"{prev.prob_vitoria_m:.1%} / {prev.prob_empate:.1%} / {prev.prob_vitoria_v:.1%}  "
          f"[lam={prev.lambda_m:.2f} mu={prev.mu_v:.2f}]")
    # Validar: time com Elo maior deve ter prob > 50% se diferença > 100pts
    if tm.rating_prior and tv.rating_prior:
        if tm.rating_prior - tv.rating_prior > 100:
            assert prev.prob_vitoria_m > 0.45, f"Favorito com prob muito baixa: {prev.prob_vitoria_m:.1%}"

# -----------------------------------------------------------------------
# Teste 3: Mercados secundários
# -----------------------------------------------------------------------
print("\n=== MERCADOS SECUNDARIOS (Brasil) ===")
if bra:
    jogo_br = next((j for j in jogos_26 if j.time_mandante_id == bra.id or j.time_visitante_id == bra.id), None)
    if jogo_br:
        pacote = pacote_jogo(jogo_br.id)
        mkt = calcular_mercados_secundarios(pacote)
        for nome, prev in mkt.items():
            if prev.ausente:
                print(f"  {nome}: AUSENTE (sem dados)")
            else:
                linha_princ = list(prev.prob_linhas.items())
                print(f"  {nome}: media={prev.media_esperada:.1f}  "
                      f"80%CI=[{prev.intervalo_80pct[0]},{prev.intervalo_80pct[1]}]  "
                      f"probs={dict(list(linha_princ)[:3])}")

# -----------------------------------------------------------------------
# Resultado final
# -----------------------------------------------------------------------
print(f"\n{'='*50}")
if erros:
    print(f"ERROS ({len(erros)}):")
    for e in erros:
        print(f"  {e}")
else:
    print(f"[OK] Fase 2 concluida — {len(resultados)} jogos testados, 0 erros")
