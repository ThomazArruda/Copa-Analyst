"""
Relatório diário via email — digest estatístico dos jogos do dia.
Sem custo de IA por execução: usa apenas Dixon-Coles para identificar tendências.

Critérios de "jogo interessante":
  FAVORITO CLARO   → uma equipe com prob vitória > 65%
  JOGO ABERTO      → nenhum com > 50% + ambas marcam > 55%
  GOLEADA ESPERADA → soma gols esperados > 3.2
  JOGO FECHADO     → soma gols esperados < 1.5
  EQUILIBRADO      → diferença entre probs < 10pp e empate > 30%
"""

import os
import logging
from datetime import datetime, date, timezone
from dotenv import load_dotenv

from src.db.repositorio import Repositorio
from src.modelos.dixon_coles import DixonColes, PrevisaoCalculada
from src.dados.ingestao import _get_repo, pacote_jogo

load_dotenv()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Análise de tendências
# ---------------------------------------------------------------------------

def _tendencias(prev: PrevisaoCalculada, time_m_nome: str, time_v_nome: str) -> list[str]:
    """Retorna lista de strings descrevendo as tendências do jogo."""
    tags = []
    pm = prev.prob_vitoria_m
    pv = prev.prob_vitoria_v
    lam_total = prev.lambda_m + prev.mu_v

    if pm > 0.65:
        tags.append(f"FAVORITO CLARO: {time_m_nome} ({pm:.0%})")
    elif pv > 0.65:
        tags.append(f"FAVORITO CLARO: {time_v_nome} ({pv:.0%})")

    if lam_total > 3.2:
        tags.append(f"GOLEADA ESPERADA ({lam_total:.1f} gols)")
    elif lam_total < 1.5:
        tags.append(f"JOGO FECHADO ({lam_total:.1f} gols esperados)")

    if prev.prob_empate > 0.32 and max(pm, pv) < 0.45:
        tags.append(f"EQUILIBRADO (empate {prev.prob_empate:.0%})")

    if prev.prob_ambas_marcam > 0.58 and max(pm, pv) < 0.55:
        tags.append(f"JOGO ABERTO (ambas marcam {prev.prob_ambas_marcam:.0%})")

    return tags


def _calcular_prev_jogo(jogo_id: int, repo: Repositorio) -> dict | None:
    """Calcula previsão Dixon-Coles para um jogo. Retorna None se falhar."""
    try:
        pacote = pacote_jogo(jogo_id)
        time_m = pacote["time_mandante"]
        time_v = pacote["time_visitante"]
        if not time_m or not time_v:
            return None

        dc = DixonColes(repo)
        prev = dc.prever_por_pacote(pacote)

        tags = _tendencias(prev, time_m.nome, time_v.nome)

        return {
            "jogo_id": jogo_id,
            "jogo": pacote["jogo"],
            "mandante": time_m.nome,
            "visitante": time_v.nome,
            "previsao": prev,
            "tendencias": tags,
            "interessante": len(tags) > 0,
            "cold_start": prev.cold_start,
        }
    except Exception as e:
        logger.warning("Falha ao calcular previsão para jogo %d: %s", jogo_id, e)
        return None


# ---------------------------------------------------------------------------
# Template HTML do email
# ---------------------------------------------------------------------------

_COR_MANDANTE  = "#1a73e8"
_COR_VISITANTE = "#e8711a"
_COR_DESTAQUE  = "#ff6b47"
_COR_FUNDO     = "#fffcfa"
_COR_CARD      = "#ffffff"


def _barra_prob(pct: float, cor: str, label: str) -> str:
    width = int(pct * 100)
    return f"""
        <div style="margin:4px 0">
          <span style="font-size:11px;color:#666;width:90px;display:inline-block">{label}</span>
          <span style="display:inline-block;background:{cor};height:12px;width:{width}px;border-radius:6px;vertical-align:middle"></span>
          <span style="font-size:12px;font-weight:700;color:{cor};margin-left:6px">{pct:.0%}</span>
        </div>"""


def _card_jogo(info: dict, destacar: bool = False) -> str:
    prev = info["previsao"]
    tags = info["tendencias"]
    border = f"border-left: 4px solid {_COR_DESTAQUE};" if destacar else "border-left: 4px solid #e0e0e0;"

    tags_html = ""
    if tags:
        tags_html = "".join(
            f'<span style="background:{_COR_DESTAQUE};color:#fff;font-size:10px;'
            f'font-weight:700;padding:2px 8px;border-radius:12px;margin:2px;display:inline-block">'
            f'{t}</span>'
            for t in tags
        )
        tags_html = f'<div style="margin:8px 0">{tags_html}</div>'

    cold_start_aviso = ""
    if info["cold_start"]:
        cold_start_aviso = (
            '<p style="font-size:10px;color:#999;margin:4px 0">'
            '⚠ Previsão baseada principalmente no rating Elo (poucos dados de Copa disponíveis)</p>'
        )

    hora = info["jogo"].hora_utc or ""
    hora_str = f" — {hora} UTC" if hora else ""

    return f"""
    <div style="background:{_COR_CARD};border-radius:12px;padding:16px;margin-bottom:12px;{border}box-shadow:0 1px 4px rgba(0,0,0,0.06)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <div>
          <span style="font-size:15px;font-weight:700;color:#1a1a1a">{info['mandante']}</span>
          <span style="font-size:13px;color:#666;margin:0 8px">×</span>
          <span style="font-size:15px;font-weight:700;color:#1a1a1a">{info['visitante']}</span>
        </div>
        <span style="font-size:11px;color:#999">Grupo {info['jogo'].grupo or '?'}{hora_str}</span>
      </div>
      {tags_html}
      <div style="margin:10px 0">
        {_barra_prob(prev.prob_vitoria_m, _COR_MANDANTE, info['mandante'][:12])}
        {_barra_prob(prev.prob_empate, '#888', 'Empate')}
        {_barra_prob(prev.prob_vitoria_v, _COR_VISITANTE, info['visitante'][:12])}
      </div>
      <div style="font-size:11px;color:#888;margin-top:8px">
        Gols esperados: <b>{prev.lambda_m:.1f}</b> — <b>{prev.mu_v:.1f}</b> &nbsp;|&nbsp;
        Over 2.5: <b>{prev.prob_over.get(2.5, 0):.0%}</b> &nbsp;|&nbsp;
        Placar provável: <b>{prev.placar_mais_provavel[0]}-{prev.placar_mais_provavel[1]}</b>
      </div>
      {cold_start_aviso}
    </div>"""


def gerar_html_digest(data_str: str, jogos_infos: list[dict]) -> str:
    """Gera o HTML completo do digest diário."""
    interessantes = [j for j in jogos_infos if j["interessante"]]
    demais = [j for j in jogos_infos if not j["interessante"]]

    cards_destaque = "".join(_card_jogo(j, destacar=True) for j in interessantes)
    cards_demais   = "".join(_card_jogo(j, destacar=False) for j in demais)

    secao_demais = ""
    if demais:
        secao_demais = f"""
        <h3 style="color:#888;font-size:13px;font-weight:600;margin:20px 0 8px;text-transform:uppercase;letter-spacing:1px">
          Demais jogos
        </h3>
        {cards_demais}"""

    n_jogos = len(jogos_infos)
    n_destaque = len(interessantes)

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Copa Analyst — {data_str}</title>
</head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:{_COR_FUNDO};margin:0;padding:20px">
  <div style="max-width:600px;margin:0 auto">

    <!-- Header -->
    <div style="text-align:center;padding:24px 0 16px">
      <h1 style="font-size:22px;font-weight:800;color:#1a1a1a;margin:0">
        Copa Analyst
      </h1>
      <p style="font-size:14px;color:#666;margin:4px 0 0">
        Digest do dia — {data_str} &nbsp;·&nbsp; {n_jogos} jogos, {n_destaque} com tendência clara
      </p>
    </div>

    <!-- Destaques -->
    {f'''<h3 style="color:{_COR_DESTAQUE};font-size:13px;font-weight:700;margin:0 0 8px;text-transform:uppercase;letter-spacing:1px">
          Tendencias Claras
        </h3>
        {cards_destaque}''' if interessantes else
     '<p style="color:#888;font-size:13px;text-align:center;padding:16px">Nenhuma tendência estatística clara nos jogos de hoje.</p>'}

    {secao_demais}

    <!-- Rodapé -->
    <div style="border-top:1px solid #e0e0e0;margin-top:24px;padding-top:16px;text-align:center">
      <p style="font-size:11px;color:#bbb;margin:0">
        Copa Analyst · Análise estatística pré-jogo · Copa do Mundo 2026<br>
        Previsões são estimativas probabilísticas, não certezas.<br>
        Para análise completa com pesquisa qualitativa, use o app antes de cada jogo.
      </p>
    </div>

  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Envio via Resend
# ---------------------------------------------------------------------------

def _enviar_resend(destinatarios: list[str], assunto: str, html: str) -> bool:
    """Envia email via Resend API. Retorna True se enviou com sucesso."""
    api_key = os.getenv("RESEND_API_KEY", "")
    remetente = os.getenv("EMAIL_REMETENTE", "onboarding@resend.dev")

    if not api_key:
        logger.error("RESEND_API_KEY não configurada")
        return False

    try:
        import resend
        resend.api_key = api_key
        resposta = resend.Emails.send({
            "from": remetente,
            "to": destinatarios,
            "subject": assunto,
            "html": html,
        })
        logger.info("Email enviado via Resend: id=%s", resposta.get("id"))
        return True
    except Exception as e:
        logger.error("Falha ao enviar email via Resend: %s", e)
        return False


# ---------------------------------------------------------------------------
# Ponto de entrada principal
# ---------------------------------------------------------------------------

def enviar_digest_diario(data_str: str = None) -> bool:
    """
    Gera e envia o digest diário para todos os destinatários configurados.

    data_str: YYYY-MM-DD (default: hoje)
    Retorna True se o email foi enviado com sucesso.
    """
    if data_str is None:
        data_str = date.today().isoformat()

    destinatarios_raw = os.getenv("EMAIL_DESTINATARIOS", "")
    if not destinatarios_raw:
        logger.error("EMAIL_DESTINATARIOS não configurado no .env")
        return False

    destinatarios = [e.strip() for e in destinatarios_raw.split(",") if e.strip()]

    repo = _get_repo()
    jogos = repo.listar_jogos_copa26()
    jogos_do_dia = [j for j in jogos if j.data == data_str]

    if not jogos_do_dia:
        logger.info("Nenhum jogo da Copa 2026 em %s", data_str)
        return False

    logger.info("Gerando digest para %s (%d jogos)", data_str, len(jogos_do_dia))

    # Calcular previsões
    infos = []
    for jogo in jogos_do_dia:
        info = _calcular_prev_jogo(jogo.id, repo)
        if info:
            infos.append(info)

    if not infos:
        logger.error("Nenhuma previsão calculada para %s", data_str)
        return False

    # Gerar HTML
    html = gerar_html_digest(data_str, infos)

    # Salvar HTML local (fallback)
    output_dir = "relatorios"
    os.makedirs(output_dir, exist_ok=True)
    html_path = f"{output_dir}/digest_{data_str}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info("Digest HTML salvo em %s", html_path)

    # Enviar email
    n_interessantes = sum(1 for i in infos if i["interessante"])
    assunto = f"Copa 2026 — {data_str} | {len(infos)} jogos, {n_interessantes} tendências claras"
    return _enviar_resend(destinatarios, assunto, html)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = sys.argv[1] if len(sys.argv) > 1 else None
    ok = enviar_digest_diario(data)
    print("Email enviado!" if ok else "Falha no envio (ver logs).")
