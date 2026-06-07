"""
Retry com backoff para chamadas à API Anthropic.

A conta opera num tier com limite de tokens de input por minuto. A camada de
pesquisa (web search) consome boa parte desse orçamento; a síntese logo em
seguida pode estourar o limite (429). Em vez de falhar, aguardamos o limite
recarregar e tentamos de novo — respeitando o header `retry-after` quando vem.
"""

import time
import logging

import anthropic

logger = logging.getLogger(__name__)

MAX_TENTATIVAS = 4
ESPERA_PADRAO_S = 60  # janela do rate limit é por minuto


def criar_mensagem_com_retry(cliente: anthropic.Anthropic, **kwargs):
    """
    Wrapper de `cliente.messages.create` que reage a RateLimitError (429)
    aguardando e tentando novamente. Demais erros sobem normalmente.
    """
    ultima_exc = None
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            return cliente.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            ultima_exc = e
            if tentativa == MAX_TENTATIVAS:
                break
            espera = _segundos_de_espera(e)
            logger.warning(
                "Rate limit (429) na tentativa %d/%d — aguardando %ds antes de tentar de novo",
                tentativa, MAX_TENTATIVAS, espera,
            )
            time.sleep(espera)
    raise ultima_exc


def _segundos_de_espera(exc: anthropic.RateLimitError) -> int:
    """Lê `retry-after` do header da resposta; cai no padrão se ausente."""
    try:
        valor = exc.response.headers.get("retry-after")
        if valor:
            return max(1, int(float(valor))) + 1  # +1s de folga
    except Exception:
        pass
    return ESPERA_PADRAO_S
