"""
Validação do contrato de saída da IA (PRD Seção 6.8).
Schema estrito com pydantic. Toda saída da IA passa por aqui antes de tocar o banco.
"""

import json
import logging
from typing import Literal, Optional
from pydantic import BaseModel, field_validator, model_validator

logger = logging.getLogger(__name__)

BANDA_AJUSTE = float(__import__("os").getenv("COPA_BAND_PP", "0.10"))

MercadoEnum = Literal[
    "resultado",
    "total_gols",
    "ambas_marcam",
    "escanteios",
    "cartoes_amarelos",
    "faltas",
    "chutes_time",
]

OrigemEnum  = Literal["calculado", "qualitativo", "hibrido"]
IncertezaEnum = Literal["baixa", "media", "alta"]


class PrevisaoItem(BaseModel):
    mercado: MercadoEnum
    previsao: str
    probabilidade_estimada: Optional[float] = None
    probabilidade_calculada_original: Optional[float] = None
    incerteza: IncertezaEnum
    origem: OrigemEnum
    justificativa: str
    fontes: list[str] = []

    @field_validator("probabilidade_estimada", "probabilidade_calculada_original")
    @classmethod
    def prob_entre_zero_e_um(cls, v):
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError(f"Probabilidade fora de [0,1]: {v}")
        return v

    @model_validator(mode="after")
    def validar_regras_banda(self):
        """Enforce PRD 2.2: regras de consistência entre origem e probabilidades."""
        est = self.probabilidade_estimada
        orig_calc = self.probabilidade_calculada_original

        if self.origem == "calculado":
            # calculado → estimada deve igualar original
            if est is not None and orig_calc is not None:
                if abs(est - orig_calc) > 1e-4:
                    logger.warning(
                        "calculado com estimada != original (%.4f vs %.4f) — igualando",
                        est, orig_calc
                    )
                    self.probabilidade_estimada = orig_calc

        elif self.origem == "hibrido":
            # híbrido → ambas presentes, diferença ≤ BANDA_AJUSTE
            if est is None or orig_calc is None:
                raise ValueError("hibrido requer probabilidade_estimada e probabilidade_calculada_original")
            diff = abs(est - orig_calc)
            if diff > BANDA_AJUSTE + 1e-4:
                logger.warning(
                    "Ajuste %.2f pp fora da banda (%.0f pp) — rebaixando para qualitativo",
                    diff * 100, BANDA_AJUSTE * 100
                )
                self.origem = "qualitativo"
                self.probabilidade_calculada_original = None

        elif self.origem == "qualitativo":
            # qualitativo → calculada_original deve ser null
            if orig_calc is not None:
                logger.warning("qualitativo com probabilidade_calculada_original não nula — zerando")
                self.probabilidade_calculada_original = None

        return self


class SaidaIA(BaseModel):
    resumo_executivo: str
    fatores_avaliados: list[str]
    fatores_ausentes: list[str]
    previsoes: list[PrevisaoItem]

    @model_validator(mode="after")
    def validar_fatores_ausentes(self):
        # fatores_ausentes não pode ser vazio se alguma previsão tem incerteza alta
        alta_incerteza = [p for p in self.previsoes if p.incerteza == "alta"]
        if alta_incerteza and not self.fatores_ausentes:
            logger.warning(
                "Previsões com incerteza alta mas fatores_ausentes vazio — possível omissão da IA"
            )
        return self


# ---------------------------------------------------------------------------
# Funções de parse e repair
# ---------------------------------------------------------------------------

def _extrair_json(texto: str) -> Optional[dict]:
    """
    Tenta extrair JSON do texto da IA.
    Estratégias em ordem:
      1. Parse direto
      2. Bloco ```json ... ```
      3. Primeiro { até último }
    """
    texto = texto.strip()

    # 1. Parse direto
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    # 2. Bloco ```json
    import re
    m = re.search(r"```json\s*([\s\S]+?)\s*```", texto)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Primeiro { até último }
    start = texto.find("{")
    end = texto.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(texto[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


def validar_saida(texto_ia: str) -> tuple[Optional[SaidaIA], list[str]]:
    """
    Valida o texto de saída da IA.
    Retorna (saida_validada, lista_de_erros).
    saida_validada é None se a validação falhou completamente.
    """
    erros = []

    dados = _extrair_json(texto_ia)
    if dados is None:
        erros.append("Não foi possível extrair JSON válido da resposta da IA")
        return None, erros

    try:
        saida = SaidaIA.model_validate(dados)
        # Filtrar previsões com mercado inválido (já rejeitadas pelo enum)
        return saida, erros
    except Exception as e:
        erros.append(f"Validação pydantic falhou: {e}")
        return None, erros


def saida_para_dict(saida: SaidaIA) -> dict:
    """Converte SaidaIA para dict serializável."""
    return saida.model_dump()
