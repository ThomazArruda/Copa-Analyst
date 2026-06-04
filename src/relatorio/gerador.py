"""
Gerador de relatório HTML standalone por jogo (PRD Seção 8).

Recebe: resultado de sintese.analisar_jogo() ou relatorio_id do banco.
Gera: arquivo HTML abrível em qualquer navegador, sem dependências externas.

Design: incerteza e origem visualmente óbvios (PRD 8.3).
  origem    → calculado=azul, qualitativo=laranja, híbrido=roxo
  incerteza → baixa=verde, media=amarelo, alta=vermelho
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.db.repositorio import Repositorio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers visuais
# ---------------------------------------------------------------------------

_CORES_ORIGEM = {
    "calculado":   "#1a73e8",
    "qualitativo": "#e8711a",
    "hibrido":     "#7c3aed",
}

_LABELS_ORIGEM = {
    "calculado":   "Calculado",
    "qualitativo": "Qualitativo",
    "hibrido":     "Híbrido",
}

_CORES_INCERTEZA = {
    "baixa": "#16a34a",
    "media": "#ca8a04",
    "alta":  "#dc2626",
}

_LABELS_INCERTEZA = {
    "baixa": "Confiança alta",
    "media": "Confiança média",
    "alta":  "Confiança baixa",
}

_LABELS_MERCADO = {
    "resultado":       "Resultado (1X2)",
    "total_gols":      "Total de Gols",
    "ambas_marcam":    "Ambas Marcam",
    "escanteios":      "Escanteios",
    "cartoes_amarelos": "Cartões Amarelos",
    "faltas":          "Faltas",
    "chutes_time":     "Chutes",
}


def _badge(texto: str, cor: str, fundo_alpha: str = "18") -> str:
    """Gera um badge colorido inline."""
    return (
        f'<span style="background:{cor}{fundo_alpha};color:{cor};'
        f'font-size:11px;font-weight:700;padding:2px 10px;border-radius:20px;'
        f'border:1px solid {cor}40;display:inline-block;margin:0 4px">'
        f'{texto}</span>'
    )


def _barra_prob(prob: float, cor: str, label: str = "") -> str:
    if prob is None:
        return ""
    w = min(int(prob * 200), 200)
    return (
        f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
        f'<span style="font-size:11px;color:#666;width:100px;flex-shrink:0">{label}</span>'
        f'<div style="background:#f0f0f0;border-radius:4px;height:10px;flex:1;max-width:200px">'
        f'<div style="background:{cor};height:10px;border-radius:4px;width:{w}px"></div></div>'
        f'<span style="font-size:12px;font-weight:700;color:{cor}">{prob:.1%}</span>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Seções do relatório
# ---------------------------------------------------------------------------

def _cabecalho(jogo, time_m, time_v, relatorio, eh_oficial: bool) -> str:
    oficial_badge = (
        '<span style="background:#16a34a18;color:#16a34a;font-size:11px;font-weight:700;'
        'padding:2px 10px;border-radius:20px;border:1px solid #16a34a40">RELATÓRIO OFICIAL</span>'
        if eh_oficial else
        '<span style="background:#ca8a0418;color:#ca8a04;font-size:11px;font-weight:700;'
        'padding:2px 10px;border-radius:20px;border:1px solid #ca8a0440">Rascunho (não oficial)</span>'
    )

    altitude_str = ""
    if jogo and jogo.altitude_m and jogo.altitude_m > 500:
        altitude_str = f' · Altitude: <b>{jogo.altitude_m:.0f}m</b>'

    return f"""
    <div style="background:linear-gradient(135deg,#1a73e8 0%,#0d47a1 100%);
                color:#fff;border-radius:16px;padding:28px 32px;margin-bottom:24px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
        <div>
          <h1 style="font-size:24px;font-weight:800;margin:0 0 4px">
            {time_m.nome if time_m else '?'} <span style="font-weight:400;opacity:.7">×</span> {time_v.nome if time_v else '?'}
          </h1>
          <p style="opacity:.8;margin:0;font-size:13px">
            Copa do Mundo 2026 · {(jogo.fase or 'Grupo').title()} {'· Grupo ' + jogo.grupo if jogo and jogo.grupo else ''}
          </p>
          <p style="opacity:.7;margin:4px 0 0;font-size:12px">
            {jogo.data if jogo else ''} {jogo.hora_utc or ''} UTC
            {'· ' + (jogo.cidade or '') if jogo and jogo.cidade else ''}{altitude_str}
          </p>
        </div>
        <div style="text-align:right">
          <div>{oficial_badge}</div>
          <p style="opacity:.6;margin:6px 0 0;font-size:10px">
            Gerado: {relatorio.get('gerado_em','')[:16].replace('T',' ')} UTC<br>
            Prompt: {relatorio.get('prompt_versao','')} · Modelo: {relatorio.get('modelo_versao','').split('-')[-1]}
          </p>
        </div>
      </div>
    </div>"""


def _resumo_executivo(texto: str) -> str:
    return f"""
    <div style="background:#f8faff;border-left:4px solid #1a73e8;border-radius:0 12px 12px 0;
                padding:16px 20px;margin-bottom:24px">
      <h2 style="font-size:13px;font-weight:700;color:#1a73e8;margin:0 0 8px;text-transform:uppercase;letter-spacing:.5px">
        Resumo Executivo
      </h2>
      <p style="font-size:14px;color:#333;margin:0;line-height:1.6">{texto}</p>
    </div>"""


def _card_previsao(prev: dict, mandante: str, visitante: str) -> str:
    mercado    = prev.get("mercado", "")
    label_mkt  = _LABELS_MERCADO.get(mercado, mercado)
    origem     = prev.get("origem", "calculado")
    incerteza  = prev.get("incerteza", "media")
    previsao   = prev.get("previsao", "")
    prob_est   = prev.get("probabilidade_estimada")
    prob_orig  = prev.get("probabilidade_calculada_original")
    justif     = prev.get("justificativa", "")
    fontes     = prev.get("fontes", [])

    cor_origem    = _CORES_ORIGEM.get(origem, "#888")
    cor_incerteza = _CORES_INCERTEZA.get(incerteza, "#888")

    badge_origem    = _badge(_LABELS_ORIGEM.get(origem, origem), cor_origem)
    badge_incerteza = _badge(_LABELS_INCERTEZA.get(incerteza, incerteza), cor_incerteza)

    # Bloco de probabilidade
    prob_html = ""
    if prob_est is not None:
        prob_html = f"""
        <div style="margin:10px 0 8px">
          <span style="font-size:28px;font-weight:800;color:{cor_origem}">{prob_est:.0%}</span>
          <span style="font-size:12px;color:#999;margin-left:4px">prob. estimada</span>
        </div>"""
        # Se híbrido: mostrar valor original → ajustado
        if origem == "hibrido" and prob_orig is not None:
            diff = (prob_est - prob_orig) * 100
            sinal = "+" if diff > 0 else ""
            prob_html += (
                f'<div style="font-size:11px;color:#7c3aed;margin-bottom:6px">'
                f'Original calculado: <b>{prob_orig:.1%}</b> '
                f'→ Ajustado: <b>{prob_est:.1%}</b> '
                f'({sinal}{diff:.1f}pp)</div>'
            )

    # Fontes
    fontes_html = ""
    if fontes:
        fontes_items = "".join(
            f'<span style="font-size:10px;background:#f0f0f0;padding:2px 6px;border-radius:4px;'
            f'margin:2px;display:inline-block">{f[:80]}</span>'
            for f in fontes[:5]
        )
        fontes_html = f'<div style="margin-top:8px">{fontes_items}</div>'

    return f"""
    <div style="background:#fff;border:1px solid #e8e8e8;border-radius:12px;padding:18px 20px;
                margin-bottom:12px;border-top:3px solid {cor_origem}">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:8px">
        <h3 style="font-size:14px;font-weight:700;color:#1a1a1a;margin:0">{label_mkt}</h3>
        <div>{badge_origem}{badge_incerteza}</div>
      </div>

      <div style="font-size:16px;font-weight:700;color:#1a1a1a;margin-bottom:4px">
        {previsao}
      </div>
      {prob_html}
      <p style="font-size:12px;color:#555;margin:8px 0 0;line-height:1.5">{justif}</p>
      {fontes_html}
    </div>"""


def _secao_fatores(avaliados: list, ausentes: list) -> str:
    itens_ok = "".join(
        f'<li style="font-size:12px;color:#333;padding:2px 0">{f}</li>' for f in avaliados
    )
    itens_nok = "".join(
        f'<li style="font-size:12px;color:#dc2626;padding:2px 0">{f}</li>' for f in ausentes
    )

    ausentes_html = ""
    if ausentes:
        ausentes_html = f"""
        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px 16px;margin-top:12px">
          <h4 style="font-size:12px;font-weight:700;color:#dc2626;margin:0 0 6px;text-transform:uppercase">
            Fatores NÃO avaliados (afetam a confiança)
          </h4>
          <ul style="margin:0;padding-left:16px">{itens_nok}</ul>
        </div>"""

    return f"""
    <div style="background:#f8f8f8;border-radius:12px;padding:16px 20px;margin-top:20px">
      <h3 style="font-size:13px;font-weight:700;color:#333;margin:0 0 8px;text-transform:uppercase;letter-spacing:.5px">
        Fatores Considerados
      </h3>
      <ul style="margin:0;padding-left:16px">{itens_ok}</ul>
      {ausentes_html}
    </div>"""


# ---------------------------------------------------------------------------
# Gerador principal
# ---------------------------------------------------------------------------

def gerar_html_relatorio(
    resultado_analise: dict,
    repo: Repositorio,
) -> str:
    """
    Gera o HTML completo do relatório a partir do resultado de sintese.analisar_jogo().
    Retorna a string HTML.
    """
    relatorio_id = resultado_analise.get("relatorio_id")
    saida        = resultado_analise.get("saida")
    jogo_id      = resultado_analise.get("jogo_id")

    if saida is None or jogo_id is None:
        raise ValueError("resultado_analise inválido — sem saida ou jogo_id")

    jogo   = repo.buscar_jogo(jogo_id)
    time_m = repo.buscar_time(jogo.time_mandante_id) if jogo else None
    time_v = repo.buscar_time(jogo.time_visitante_id) if jogo else None

    # Buscar metadados do relatório
    relatorio_meta = {}
    if relatorio_id:
        with repo._conn() as conn:
            row = conn.execute(
                "SELECT * FROM relatorios WHERE id = ?", (relatorio_id,)
            ).fetchone()
            if row:
                relatorio_meta = dict(row)

    eh_oficial = bool(relatorio_meta.get("eh_relatorio_oficial", 0))
    saida_dict = saida.model_dump() if hasattr(saida, "model_dump") else saida

    # Cards de previsão
    mandante_nome = time_m.nome if time_m else "Mandante"
    visitante_nome = time_v.nome if time_v else "Visitante"
    cards = "".join(
        _card_previsao(p, mandante_nome, visitante_nome)
        for p in saida_dict.get("previsoes", [])
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Copa Analyst — {mandante_nome} × {visitante_nome}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #fffcfa;
      margin: 0;
      padding: 20px;
      color: #1a1a1a;
    }}
    .container {{ max-width: 720px; margin: 0 auto; }}
    h2 {{ font-size: 15px; font-weight: 700; color: #333; margin: 24px 0 12px;
          text-transform: uppercase; letter-spacing: .5px; border-bottom: 2px solid #e8e8e8;
          padding-bottom: 6px; }}
    @media (max-width: 600px) {{
      body {{ padding: 12px; }}
      .container {{ max-width: 100%; }}
    }}
  </style>
</head>
<body>
<div class="container">

  {_cabecalho(jogo, time_m, time_v, relatorio_meta, eh_oficial)}
  {_resumo_executivo(saida_dict.get('resumo_executivo', ''))}

  <h2>Previsões por Mercado</h2>
  {cards}

  {_secao_fatores(
      saida_dict.get('fatores_avaliados', []),
      saida_dict.get('fatores_ausentes', [])
  )}

  <div style="text-align:center;padding:24px 0 8px;color:#bbb;font-size:11px">
    Copa Analyst · Análise estatística pré-jogo · Copa do Mundo 2026<br>
    Previsões são estimativas probabilísticas, não certezas.
  </div>

</div>
</body>
</html>"""
    return html


def salvar_relatorio(resultado_analise: dict, repo: Repositorio,
                     diretorio: str = "relatorios") -> str:
    """
    Gera e salva o HTML do relatório. Retorna o caminho do arquivo.
    """
    jogo_id = resultado_analise.get("jogo_id")
    jogo = repo.buscar_jogo(jogo_id) if jogo_id else None
    time_m = repo.buscar_time(jogo.time_mandante_id) if jogo else None
    time_v = repo.buscar_time(jogo.time_visitante_id) if jogo else None

    nm = (time_m.nome if time_m else "time_m").replace(" ", "_").lower()
    nv = (time_v.nome if time_v else "time_v").replace(" ", "_").lower()
    data = jogo.data if jogo else "0000-00-00"
    nome_arquivo = f"relatorio_{data}_{nm}_vs_{nv}.html"

    Path(diretorio).mkdir(parents=True, exist_ok=True)
    caminho = os.path.join(diretorio, nome_arquivo)

    html = gerar_html_relatorio(resultado_analise, repo)
    Path(caminho).write_text(html, encoding="utf-8")
    logger.info("Relatório salvo: %s", caminho)
    return caminho
