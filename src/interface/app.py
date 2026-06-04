"""
Copa Analyst — Interface Streamlit (Fase 5).
Uso: streamlit run src/interface/app.py
"""

import os
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.WARNING)

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Copa Analyst",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS global
st.markdown("""
<style>
  .main { background: #fffcfa; }
  [data-testid="stSidebar"] { background: #1a1a2e; }
  [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
  .metric-card {
    background: white; border-radius: 12px; padding: 16px;
    border: 1px solid #e8e8e8; margin-bottom: 8px;
  }
  .jogo-card {
    background: white; border-radius: 12px; padding: 16px 20px;
    border: 1px solid #e8e8e8; margin-bottom: 10px;
    border-left: 4px solid #1a73e8;
  }
  .tag-favorito { background:#1a73e818; color:#1a73e8; padding:2px 10px;
    border-radius:20px; font-size:11px; font-weight:700; }
  .tag-goleada  { background:#dc262618; color:#dc2626; padding:2px 10px;
    border-radius:20px; font-size:11px; font-weight:700; }
  .tag-fechado  { background:#16a34a18; color:#16a34a; padding:2px 10px;
    border-radius:20px; font-size:11px; font-weight:700; }
  .tag-equilibrado { background:#ca8a0418; color:#ca8a04; padding:2px 10px;
    border-radius:20px; font-size:11px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Cache de repositório
# ---------------------------------------------------------------------------

@st.cache_resource
def get_repo():
    from src.dados.ingestao import _get_repo
    return _get_repo()


@st.cache_data(ttl=300)
def listar_jogos_copa26():
    repo = get_repo()
    jogos = repo.listar_jogos_copa26()
    result = []
    for j in jogos:
        tm = repo.buscar_time(j.time_mandante_id)
        tv = repo.buscar_time(j.time_visitante_id)
        result.append({
            "id": j.id, "data": j.data, "hora": j.hora_utc or "",
            "mandante": tm.nome if tm else "?",
            "visitante": tv.nome if tv else "?",
            "grupo": j.grupo or "?", "fase": j.fase or "grupo",
            "cidade": j.cidade or "", "placar_m": j.placar_mandante,
            "placar_v": j.placar_visitante,
        })
    return result


@st.cache_data(ttl=60)
def calcular_previsao_rapida(jogo_id: int):
    from src.dados.ingestao import pacote_jogo
    from src.modelos.dixon_coles import DixonColes
    from src.relatorio.email_diario import _tendencias
    repo = get_repo()
    try:
        pacote = pacote_jogo(jogo_id)
        dc = DixonColes(repo)
        prev = dc.prever_por_pacote(pacote)
        tm = pacote["time_mandante"]
        tv = pacote["time_visitante"]
        tags = _tendencias(prev, tm.nome if tm else "", tv.nome if tv else "")
        return {"prev": prev, "tags": tags, "ok": True}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ⚽ Copa Analyst")
    st.markdown("Copa do Mundo 2026")
    st.divider()

    pagina = st.radio(
        "Navegação",
        ["Jogos do Dia", "Análise Completa", "Digest Email", "Calibração", "Atualizar Dados"],
        label_visibility="collapsed",
    )

    st.divider()
    mock_mode = os.getenv("MOCK_AI", "").lower() == "true"
    if mock_mode:
        st.warning("MOCK_AI=true\nSem chamadas à API")
    else:
        st.success("Modo produção")

    st.caption(f"Hoje: {date.today().isoformat()}")

# ---------------------------------------------------------------------------
# Página: Jogos do Dia
# ---------------------------------------------------------------------------

if pagina == "Jogos do Dia":
    st.title("Jogos do Dia")

    todos_jogos = listar_jogos_copa26()
    datas_disponiveis = sorted(set(j["data"] for j in todos_jogos))

    col1, col2 = st.columns([2, 1])
    with col1:
        data_sel = st.date_input(
            "Data",
            value=date.today(),
            min_value=date(2026, 6, 11),
            max_value=date(2026, 7, 19),
        )
    with col2:
        mostrar_previsao = st.checkbox("Mostrar previsões", value=True)

    data_str = data_sel.isoformat()
    jogos_dia = [j for j in todos_jogos if j["data"] == data_str]

    if not jogos_dia:
        st.info(f"Nenhum jogo da Copa 2026 em {data_str}.")
    else:
        st.markdown(f"**{len(jogos_dia)} jogos em {data_str}**")
        for jogo in jogos_dia:
            placar_str = ""
            if jogo["placar_m"] is not None:
                placar_str = f"**{jogo['placar_m']} – {jogo['placar_v']}**"

            with st.container():
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.markdown(
                        f"**{jogo['mandante']}** × **{jogo['visitante']}**  \n"
                        f"Grupo {jogo['grupo']} · {jogo['hora']} UTC · {jogo['cidade']}"
                    )
                with c2:
                    if placar_str:
                        st.markdown(f"Resultado: {placar_str}")
                    elif mostrar_previsao:
                        dados = calcular_previsao_rapida(jogo["id"])
                        if dados["ok"]:
                            prev = dados["prev"]
                            st.markdown(
                                f"{prev.prob_vitoria_m:.0%} / {prev.prob_empate:.0%} / {prev.prob_vitoria_v:.0%}  \n"
                                f"Gols: {prev.lambda_m:.1f}–{prev.mu_v:.1f}  ·  O2.5: {prev.prob_over.get(2.5,0):.0%}"
                            )
                            for tag in dados["tags"]:
                                st.markdown(f":small_orange_diamond: {tag}")
                with c3:
                    if st.button("Analisar", key=f"btn_{jogo['id']}"):
                        st.session_state["jogo_id_analise"] = jogo["id"]
                        st.session_state["pagina_redirect"] = "Análise Completa"
                        st.rerun()

                st.divider()


# ---------------------------------------------------------------------------
# Página: Análise Completa
# ---------------------------------------------------------------------------

elif pagina == "Análise Completa":
    st.title("Análise Completa de Jogo")

    todos_jogos = listar_jogos_copa26()

    # Construir lista de opções
    opcoes = {
        f"{j['data']} | Grupo {j['grupo']} | {j['mandante']} × {j['visitante']}": j["id"]
        for j in todos_jogos
    }
    opcoes_list = list(opcoes.keys())

    # Pré-selecionar se veio da página de jogos
    idx_default = 0
    if "jogo_id_analise" in st.session_state:
        jid = st.session_state["jogo_id_analise"]
        for i, (label, vid) in enumerate(opcoes.items()):
            if vid == jid:
                idx_default = i
                break

    sel_label = st.selectbox("Selecionar jogo", opcoes_list, index=idx_default)
    jogo_id = opcoes[sel_label]

    # Preview rápida
    dados_rapidos = calcular_previsao_rapida(jogo_id)
    if dados_rapidos["ok"]:
        prev = dados_rapidos["prev"]
        col1, col2, col3, col4 = st.columns(4)
        nm = sel_label.split("|")[-1].split("×")[0].strip()
        nv = sel_label.split("|")[-1].split("×")[-1].strip()
        col1.metric(f"Vitória {nm[:12]}", f"{prev.prob_vitoria_m:.0%}")
        col2.metric("Empate", f"{prev.prob_empate:.0%}")
        col3.metric(f"Vitória {nv[:12]}", f"{prev.prob_vitoria_v:.0%}")
        col4.metric("Over 2.5", f"{prev.prob_over.get(2.5,0):.0%}")

        if prev.cold_start:
            st.warning("Cold start: parâmetros baseados principalmente no rating Elo. Dados de Copa escassos.")

    st.divider()

    # Relatórios existentes
    repo = get_repo()
    with repo._conn() as conn:
        relatorios = conn.execute(
            "SELECT id, gerado_em, eh_relatorio_oficial, prompt_versao FROM relatorios "
            "WHERE jogo_id = ? ORDER BY gerado_em DESC",
            (jogo_id,)
        ).fetchall()

    if relatorios:
        st.markdown(f"**{len(relatorios)} relatório(s) existente(s) para este jogo:**")
        for rel in relatorios:
            oficial = "OFICIAL" if rel["eh_relatorio_oficial"] else "rascunho"
            label = f"{rel['gerado_em'][:16]} — {oficial} (prompt {rel['prompt_versao']})"
            if st.button(f"Ver: {label}", key=f"ver_{rel['id']}"):
                st.session_state[f"rel_ver_{jogo_id}"] = rel["id"]

        # Mostrar relatório selecionado
        rel_id_ver = st.session_state.get(f"rel_ver_{jogo_id}")
        if rel_id_ver:
            with repo._conn() as conn:
                row = conn.execute(
                    "SELECT conteudo FROM relatorios WHERE id = ?", (rel_id_ver,)
                ).fetchone()
            if row:
                conteudo = row["conteudo"]
                # Tentar montar HTML completo a partir do JSON do conteúdo
                try:
                    dados = json.loads(conteudo)
                    from src.relatorio.gerador import gerar_html_relatorio
                    from src.ia.validacao import SaidaIA
                    saida = SaidaIA.model_validate(dados)
                    resultado_sim = {"sucesso": True, "relatorio_id": rel_id_ver,
                                     "saida": saida, "jogo_id": jogo_id}
                    html = gerar_html_relatorio(resultado_sim, repo)
                    components.html(html, height=800, scrolling=True)
                except Exception:
                    st.text_area("Conteúdo bruto", conteudo, height=400)

            col_of1, col_of2 = st.columns(2)
            if col_of1.button("Marcar como Oficial", key=f"oficial_{rel_id_ver}"):
                repo.marcar_relatorio_oficial(rel_id_ver)
                st.success("Relatório marcado como oficial.")
                st.rerun()

        st.divider()

    # Botão para nova análise
    st.markdown("### Gerar nova análise")
    if st.button("Analisar agora (chama IA)", type="primary", use_container_width=True):
        from src.ia.sintese import analisar_jogo
        from src.relatorio.gerador import gerar_html_relatorio, salvar_relatorio

        progress = st.progress(0, text="Coletando dados...")
        try:
            progress.progress(20, text="Pesquisando (escalacao, lesoes, arbitro)...")
            resultado = analisar_jogo(jogo_id, repo)
            progress.progress(70, text="Gerando relatorio...")

            if not resultado["sucesso"]:
                st.error(f"Analise falhou: {resultado.get('erros')}")
            else:
                html = gerar_html_relatorio(resultado, repo)
                caminho = salvar_relatorio(resultado, repo)
                progress.progress(100, text="Pronto!")
                st.success(f"Relatório gerado: {caminho}")
                components.html(html, height=800, scrolling=True)
                # limpar cache para mostrar novo relatório
                st.cache_data.clear()
        except Exception as e:
            st.error(f"Erro: {e}")
        finally:
            progress.empty()


# ---------------------------------------------------------------------------
# Página: Digest Email
# ---------------------------------------------------------------------------

elif pagina == "Digest Email":
    st.title("Digest Diário por Email")

    col1, col2 = st.columns([2, 1])
    with col1:
        data_digest = st.date_input(
            "Data do digest",
            value=date.today(),
            min_value=date(2026, 6, 11),
            max_value=date(2026, 7, 19),
        )
    with col2:
        st.markdown("&nbsp;")
        apenas_preview = st.checkbox("Só preview (não enviar)", value=True)

    data_str = data_digest.isoformat()

    if st.button("Gerar Digest", type="primary"):
        from src.relatorio.email_diario import (
            _calcular_prev_jogo, gerar_html_digest, _enviar_resend
        )
        repo = get_repo()
        jogos_todos = listar_jogos_copa26()
        jogos_dia = [j for j in jogos_todos if j["data"] == data_str]

        if not jogos_dia:
            st.warning(f"Nenhum jogo em {data_str}.")
        else:
            with st.spinner(f"Calculando previsões para {len(jogos_dia)} jogos..."):
                infos = []
                for j_dict in jogos_dia:
                    info = _calcular_prev_jogo(j_dict["id"], repo)
                    if info:
                        infos.append(info)

            n_int = sum(1 for i in infos if i["interessante"])
            st.info(f"{len(infos)} jogos calculados, **{n_int} com tendência clara**.")

            html = gerar_html_digest(data_str, infos)

            # Salvar localmente sempre
            os.makedirs("relatorios", exist_ok=True)
            html_path = f"relatorios/digest_{data_str}.html"
            Path(html_path).write_text(html, encoding="utf-8")

            # Preview
            st.markdown("### Preview do email")
            components.html(html, height=700, scrolling=True)

            if not apenas_preview:
                destinatarios_raw = os.getenv("EMAIL_DESTINATARIOS", "")
                if not destinatarios_raw:
                    st.error("EMAIL_DESTINATARIOS não configurado no .env")
                else:
                    destinatarios = [e.strip() for e in destinatarios_raw.split(",") if e.strip()]
                    n_int_count = sum(1 for i in infos if i["interessante"])
                    assunto = f"Copa 2026 — {data_str} | {len(infos)} jogos, {n_int_count} tendencias claras"
                    ok = _enviar_resend(destinatarios, assunto, html)
                    if ok:
                        st.success(f"Email enviado para {len(destinatarios)} destinatário(s)!")
                    else:
                        st.error("Falha no envio. Verifique RESEND_API_KEY no .env.")


# ---------------------------------------------------------------------------
# Página: Atualizar Dados
# ---------------------------------------------------------------------------

elif pagina == "Calibração":
    st.title("Painel de Calibração")
    st.caption(
        "Avalia a qualidade das previsões usando Brier score e log-loss. "
        "Apenas relatórios marcados como **oficiais** entram nesta análise (PRD 9.1)."
    )

    repo = get_repo()

    # Atualizar resultados antes de calcular
    col_upd, _ = st.columns([1, 3])
    if col_upd.button("Atualizar resultados agora"):
        from src.dados.resultados import atualizar_resultados_automatico
        with st.spinner("Buscando resultados..."):
            r = atualizar_resultados_automatico(repo)
        st.success(f"{r['jogos']} jogos, {r['previsoes']} previsões atualizadas.")
        st.cache_data.clear()

    # Entrada manual de resultado
    with st.expander("Inserir resultado manualmente"):
        todos_jogos = listar_jogos_copa26()
        jogos_sem_resultado = [
            j for j in todos_jogos
            if j["placar_m"] is None
        ]
        if not jogos_sem_resultado:
            st.info("Todos os jogos com relatório oficial já têm resultado.")
        else:
            opcoes_manual = {
                f"{j['data']} | {j['mandante']} × {j['visitante']}": j["id"]
                for j in jogos_sem_resultado
            }
            sel = st.selectbox("Jogo", list(opcoes_manual.keys()), key="manual_jogo")
            c1, c2 = st.columns(2)
            gols_m = c1.number_input("Gols mandante", min_value=0, max_value=20, value=0)
            gols_v = c2.number_input("Gols visitante", min_value=0, max_value=20, value=0)
            if st.button("Salvar resultado manual"):
                from src.dados.resultados import preencher_resultado_real_jogo
                jid = opcoes_manual[sel]
                n = preencher_resultado_real_jogo(jid, int(gols_m), int(gols_v), repo)
                st.success(f"Resultado salvo. {n} previsões atualizadas.")
                st.cache_data.clear()

    st.divider()

    # Calcular e exibir métricas
    from src.validacao.calibracao import calcular_calibracao, pontos_calibracao

    painel = calcular_calibracao(repo)

    # Avisos de ruído e leakage (PRD 9.2 e 9.5)
    if painel.aviso_ruido:
        st.warning(f"Aviso estatístico: {painel.aviso_ruido}")
    if painel.alerta_leakage:
        st.error(f"Possível data leakage: {painel.alerta_leakage}")

    col1, col2 = st.columns(2)
    col1.metric("Relatórios oficiais", painel.total_relatorios_oficiais)
    col2.metric("Previsões avaliadas", painel.total_previsoes_avaliadas)

    if painel.total_previsoes_avaliadas == 0:
        st.info(
            "Nenhuma previsão com resultado disponível ainda. "
            "O painel ficará ativo após os primeiros jogos da Copa."
        )
    else:
        st.markdown("### Métricas por mercado")
        st.caption(
            "Brier score: 0.0 = perfeito, 0.25 = referência (sempre prever 50%). "
            "Log-loss: menor é melhor. Acerto binário é só display — não é a métrica. (PRD 9.3)"
        )

        for m in painel.por_mercado:
            ruido_tag = " *(ruído — N pequeno)*" if m.ruido_alto else ""
            leakage_tag = " :red[VERIFICAR LEAKAGE]" if m.alerta_leakage else ""

            with st.expander(
                f"**{m.mercado}** — N={m.n} | Brier={m.brier_score:.3f} | "
                f"Log-loss={m.log_loss:.3f}{ruido_tag}{leakage_tag}"
            ):
                c1, c2, c3 = st.columns(3)
                c1.metric("Brier Score", f"{m.brier_score:.3f}",
                          help="0=perfeito, 0.25=baseline (sempre 50%)")
                c2.metric("Log-loss", f"{m.log_loss:.3f}",
                          help="Menor é melhor. Penaliza confiança errada.")
                c3.metric("Acerto binário (display)", f"{m.acerto_binario:.0%}",
                          help="Apenas para display. Não é métrica de qualidade. (PRD 9.3)")

                if m.ruido_alto:
                    st.caption(
                        f"Com {m.n} amostras, estes números têm alta variância estatística. "
                        "Não tire conclusões até ter pelo menos 20 previsões por mercado."
                    )

        # Gráfico de calibração
        pontos = pontos_calibracao(repo)
        if len(pontos) >= 3:
            st.markdown("### Gráfico de Calibração")
            st.caption(
                "Ideal: pontos na diagonal (probabilidade prevista = frequência real). "
                "Pontos acima = modelo sub-confiante. Abaixo = super-confiante."
            )
            import pandas as pd
            df = pd.DataFrame(pontos)
            df["diagonal"] = df["prob_prevista"]
            st.line_chart(
                df.set_index("prob_prevista")[["freq_real", "diagonal"]],
                use_container_width=True,
            )


elif pagina == "Atualizar Dados":
    st.title("Atualizar Dados")

    st.markdown("""
    Use esta página para manter o banco de dados atualizado durante a Copa.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Resultados Copa 2026")
        st.caption("Puxa resultados atualizados via TheSportsDB. Rodar após cada rodada.")
        if st.button("Atualizar resultados", use_container_width=True):
            from src.dados.ingestao import atualizar_resultados_copa26
            with st.spinner("Atualizando..."):
                n = atualizar_resultados_copa26()
            st.success(f"{n} resultados atualizados.")
            st.cache_data.clear()

    with col2:
        st.markdown("### Rating Prior (Elo)")
        st.caption("Recalcula o Elo de todos os times com os dados no banco.")
        if st.button("Recalcular Elo", use_container_width=True):
            from src.modelos.rating_prior import RatingPrior
            with st.spinner("Calculando..."):
                rp = RatingPrior(get_repo())
                n = rp.calcular_e_salvar()
            st.success(f"Elo atualizado para {n} times.")
            st.cache_data.clear()

    st.divider()
    st.markdown("### Status do banco")

    repo = get_repo()
    with repo._conn() as conn:
        total_jogos = conn.execute("SELECT COUNT(*) FROM jogos").fetchone()[0]
        total_copa26 = conn.execute(
            "SELECT COUNT(*) FROM jogos WHERE competicao='copa_2026'"
        ).fetchone()[0]
        total_relatorios = conn.execute("SELECT COUNT(*) FROM relatorios").fetchone()[0]
        total_previsoes = conn.execute("SELECT COUNT(*) FROM previsoes").fetchone()[0]
        total_stats = conn.execute("SELECT COUNT(*) FROM estatisticas_jogo").fetchone()[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Jogos total", total_jogos)
    c2.metric("Fixtures Copa 2026", total_copa26)
    c3.metric("Relatórios", total_relatorios)
    c4.metric("Previsões", total_previsoes)
    c5.metric("Stats no banco", total_stats)

    # Top times por Elo
    st.markdown("### Top 10 — Rating Elo atual")
    times = sorted(repo.listar_times(), key=lambda t: t.rating_prior or 0, reverse=True)
    top10 = [(t.nome, round(t.rating_prior or 0)) for t in times[:10] if t.rating_prior]
    if top10:
        for i, (nome, elo) in enumerate(top10, 1):
            st.markdown(f"{i}. **{nome}** — {elo} Elo")
