# Operações de leitura/escrita nos CSVs do sistema.
#
# Cada função trata erros de forma controlada (FileNotFoundError, dados
# corrompidos, tipos inválidos) e retorna resultados tipados.
# O agente nunca manipula CSV diretamente — sempre via estas funções.

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import CLIENTS_CSV, REQUESTS_CSV, SCORE_LIMIT_CSV

logger = logging.getLogger("banco_agil.csv_tools")


def read_clients() -> pd.DataFrame:
    """Carrega a base de clientes."""
    try:
        df = pd.read_csv(CLIENTS_CSV, dtype={"cpf": str})
        logger.info("Clientes carregados: %d registros", len(df))
        return df
    except FileNotFoundError:
        logger.error("Arquivo de clientes não encontrado: %s", CLIENTS_CSV)
        raise
    except Exception as e:
        logger.error("Erro ao ler clientes: %s", e)
        raise


def authenticate_client(cpf: str, birth_date: str) -> dict | None:
    """Autentica cliente por CPF + data de nascimento.

    Args:
        cpf: CPF sem formatação (11 dígitos).
        birth_date: Data de nascimento no formato YYYY-MM-DD.

    Returns:
        Dict com dados do cliente se autenticado, None se falhar.
    """
    cpf_clean = cpf.replace(".", "").replace("-", "").strip()

    # Normaliza a data de nascimento para YYYY-MM-DD
    birth_normalized = _normalize_date(birth_date)
    if not birth_normalized:
        logger.warning("Data de nascimento inválida: '%s'", birth_date)
        return None

    try:
        df = read_clients()
        df["cpf"] = df["cpf"].astype(str).str.strip()
        df["data_nascimento"] = df["data_nascimento"].astype(str).str.strip()

        match = df[
            (df["cpf"] == cpf_clean) & (df["data_nascimento"] == birth_normalized)
        ]

        if match.empty:
            logger.info("Autenticação falhou para CPF=%s", cpf_clean[:4] + "***")
            return None

        client = match.iloc[0].to_dict()
        logger.info("Cliente autenticado: %s", client["nome"])
        return client
    except Exception as e:
        logger.error("Erro na autenticação: %s", e)
        return None


def _normalize_date(date_str: str) -> str | None:
    """Normaliza diversos formatos de data para YYYY-MM-DD."""
    date_str = date_str.strip()
    formats = [
        "%Y-%m-%d",      # 1990-05-15
        "%d/%m/%Y",      # 15/05/1990
        "%d-%m-%Y",      # 15-05-1990
        "%d.%m.%Y",      # 15.05.1990
        "%d %m %Y",      # 15 05 1990
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def get_client_credit(cpf: str) -> dict | None:
    """Consulta limite de crédito e score do cliente.

    Returns:
        Dict com {cpf, nome, score, limite_credito} ou None.
    """
    cpf_clean = cpf.replace(".", "").replace("-", "").strip()
    try:
        df = read_clients()
        df["cpf"] = df["cpf"].astype(str).str.strip()
        match = df[df["cpf"] == cpf_clean]

        if match.empty:
            return None

        row = match.iloc[0]
        return {
            "cpf": cpf_clean,
            "nome": row["nome"],
            "score": int(row["score"]),
            "limite_credito": float(row["limite_credito"]),
        }
    except Exception as e:
        logger.error("Erro ao consultar crédito: %s", e)
        return None


def check_score_limit(score: int, requested_limit: float) -> dict:
    """Verifica se o score permite o limite solicitado.

    Returns:
        Dict com {approved, max_allowed, reason}.
    """
    try:
        df = pd.read_csv(SCORE_LIMIT_CSV)
        for _, row in df.iterrows():
            if row["score_minimo"] <= score <= row["score_maximo"]:
                max_allowed = float(row["limite_maximo"])
                approved = requested_limit <= max_allowed
                return {
                    "approved": approved,
                    "max_allowed": max_allowed,
                    "reason": (
                        f"Score {score} permite limite de até R$ {max_allowed:,.2f}."
                        if approved
                        else f"Score {score} permite no máximo R$ {max_allowed:,.2f}. "
                        f"Solicitado: R$ {requested_limit:,.2f}."
                    ),
                }
        return {
            "approved": False,
            "max_allowed": 0,
            "reason": f"Score {score} fora das faixas configuradas.",
        }
    except FileNotFoundError:
        logger.error("Tabela de score/limite não encontrada: %s", SCORE_LIMIT_CSV)
        return {
            "approved": False,
            "max_allowed": 0,
            "reason": "Erro interno: tabela de limites indisponível.",
        }


def register_credit_request(
    cpf: str,
    current_limit: float,
    requested_limit: float,
    status: str,
) -> bool:
    """Registra solicitação de aumento de limite no CSV.

    Args:
        cpf: CPF do cliente.
        current_limit: Limite atual.
        requested_limit: Novo limite solicitado.
        status: 'pendente', 'aprovado' ou 'rejeitado'.

    Returns:
        True se registrou com sucesso.
    """
    try:
        timestamp = datetime.now().isoformat()
        row = [cpf, timestamp, current_limit, requested_limit, status]

        file_exists = REQUESTS_CSV.exists()
        with open(REQUESTS_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "cpf_cliente",
                    "data_hora_solicitacao",
                    "limite_atual",
                    "novo_limite_solicitado",
                    "status_pedido",
                ])
            writer.writerow(row)

        logger.info(
            "Solicitação registrada: CPF=%s limite=%s→%s status=%s",
            cpf[:4] + "***",
            current_limit,
            requested_limit,
            status,
        )
        return True
    except Exception as e:
        logger.error("Erro ao registrar solicitação: %s", e)
        return False


def update_client_score(cpf: str, new_score: int) -> bool:
    """Atualiza o score de um cliente na base.

    Args:
        cpf: CPF do cliente.
        new_score: Novo score calculado (0-1000).

    Returns:
        True se atualizou com sucesso.
    """
    cpf_clean = cpf.replace(".", "").replace("-", "").strip()
    try:
        df = read_clients()
        df["cpf"] = df["cpf"].astype(str).str.strip()
        mask = df["cpf"] == cpf_clean

        if not mask.any():
            logger.warning("Cliente não encontrado para atualizar score: %s", cpf_clean[:4] + "***")
            return False

        new_score = max(0, min(1000, new_score))  # Clamp 0-1000
        df.loc[mask, "score"] = new_score
        df.to_csv(CLIENTS_CSV, index=False)

        logger.info("Score atualizado: CPF=%s novo_score=%d", cpf_clean[:4] + "***", new_score)
        return True
    except Exception as e:
        logger.error("Erro ao atualizar score: %s", e)
        return False
