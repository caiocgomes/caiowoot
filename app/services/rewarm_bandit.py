"""Bandit contextual para alocar leads de rewarm entre janelas noon/evening.

Thompson sampling com regressão logística bayesiana por braço.
Laplace approximation via Newton-Raphson em numpy puro.
"""

import json
import logging
import random
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

import numpy as np

from app.config import now_local, settings
from app.database import get_db
from app.services.claude_client import get_anthropic_client

logger = logging.getLogger(__name__)

ARMS = ("noon", "evening")
SLOT_HOURS = {"noon": (12, 30), "evening": (18, 30)}
JITTER_MINUTES = 15
WARMUP_THRESHOLD = 40
PRIOR_SIGMA = 3.0

# hora_resp_tipica_utc: mediana das horas (em horas decimais, base UTC pois messages.created_at é UTC)
# do horário em que o lead respondeu historicamente. Apenas um identificador do padrão — a semântica
# local (almoço, fim de expediente) é codificada nos SLOT_HOURS, não nessa feature.
FEATURE_NAMES = ("intercept", "has_history", "hora_resp_tipica_utc", "estagio_link")

PRODUCTIVE_TOOL_NAME = "classify_response"
PRODUCTIVE_TOOL = {
    "name": PRODUCTIVE_TOOL_NAME,
    "description": "Classifica se a resposta do lead foi produtiva ou não.",
    "input_schema": {
        "type": "object",
        "properties": {
            "productive": {
                "type": "boolean",
                "description": "True se resposta avança a conversa (pergunta, interesse, pedido de info). False se passiva, negativa ou hostil.",
            },
            "reason": {
                "type": "string",
                "description": "Justificativa em 1 frase.",
            },
        },
        "required": ["productive", "reason"],
    },
}

PRODUCTIVE_SYSTEM_PROMPT = """Você classifica se a resposta de um lead a uma mensagem de reaquecimento foi produtiva.

PRODUTIVA: pergunta sobre o produto, pedido de informação, sinal de interesse ativo, agendamento, dúvida real sobre o curso, engajamento que move a conversa adiante.

NÃO-PRODUTIVA: "ok", "obrigado", "vou ver", "depois falo", "não tenho interesse", "para de mandar", hostilidade, resposta automática, reação passiva sem intenção.

Na dúvida, classifique como NÃO-PRODUTIVA. Retorne via tool classify_response com boolean productive e reason curta."""


# ----- Feature extraction -----

async def extract_features(db, conversation_id: int) -> dict[str, float]:
    """Calcula features contextuais do lead para decisão de braço."""
    cursor = await db.execute(
        """SELECT created_at FROM messages
           WHERE conversation_id = ? AND direction = 'inbound'
           ORDER BY created_at""",
        (conversation_id,),
    )
    rows = await cursor.fetchall()

    hours: list[float] = []
    for r in rows:
        try:
            dt = datetime.fromisoformat(r["created_at"])
            hours.append(dt.hour + dt.minute / 60.0)
        except (ValueError, TypeError):
            continue

    if hours:
        has_history = 1.0
        hora_resp_tipica_utc = float(median(hours))
    else:
        has_history = 0.0
        hora_resp_tipica_utc = 0.0

    stage_cursor = await db.execute(
        "SELECT funnel_stage FROM conversations WHERE id = ?",
        (conversation_id,),
    )
    stage_row = await stage_cursor.fetchone()
    stage = (stage_row["funnel_stage"] if stage_row else None) or ""
    estagio_link = 1.0 if stage == "link_sent" else 0.0

    return {
        "intercept": 1.0,
        "has_history": has_history,
        "hora_resp_tipica_utc": hora_resp_tipica_utc,
        "estagio_link": estagio_link,
    }


def features_to_vector(features: dict[str, float]) -> np.ndarray:
    return np.array([features[name] for name in FEATURE_NAMES], dtype=float)


# ----- Thompson sampling -----

def _sigmoid(z):
    z = np.asarray(z, dtype=float)
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


def _laplace_fit(
    X: np.ndarray,
    y: np.ndarray,
    prior_sigma: float = PRIOR_SIGMA,
    max_iter: int = 50,
    tol: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray]:
    """Regressão logística bayesiana via Laplace approximation.

    Retorna (mu, Sigma) onde mu é o MAP (Newton-Raphson) e Sigma é H^{-1} no MAP.
    """
    d = X.shape[1]
    w = np.zeros(d, dtype=float)
    inv_prior_var = 1.0 / (prior_sigma ** 2)

    for _ in range(max_iter):
        p = _sigmoid(X @ w)
        g = X.T @ (p - y) + inv_prior_var * w
        W = p * (1.0 - p)
        H = (X.T * W) @ X + inv_prior_var * np.eye(d)
        try:
            delta = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            break
        w_new = w - delta
        if np.linalg.norm(delta) < tol:
            w = w_new
            break
        w = w_new

    p = _sigmoid(X @ w)
    W = p * (1.0 - p)
    H = (X.T * W) @ X + inv_prior_var * np.eye(d)
    try:
        Sigma = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        Sigma = (prior_sigma ** 2) * np.eye(d)

    return w, Sigma


async def _load_bandit_state(db, arm: str) -> tuple[np.ndarray, np.ndarray, int]:
    """Retorna (mu, Sigma, n_obs) para o braço. Se não existe, retorna prior."""
    cursor = await db.execute(
        "SELECT mu_json, sigma_json, n_obs FROM bandit_state WHERE arm = ?",
        (arm,),
    )
    row = await cursor.fetchone()
    d = len(FEATURE_NAMES)
    if row is None:
        return np.zeros(d), (PRIOR_SIGMA ** 2) * np.eye(d), 0
    mu = np.array(json.loads(row["mu_json"]), dtype=float)
    sigma_flat = np.array(json.loads(row["sigma_json"]), dtype=float)
    Sigma = sigma_flat.reshape(d, d)
    return mu, Sigma, int(row["n_obs"])


async def _count_total_dispatches_closed(db) -> int:
    cursor = await db.execute(
        "SELECT COUNT(*) AS c FROM rewarm_dispatches WHERE closed_at IS NOT NULL"
    )
    row = await cursor.fetchone()
    return int(row["c"]) if row else 0


async def sample_arm(db, features: dict[str, float]) -> str:
    """Escolhe braço via Thompson sampling. Em warmup usa 50/50 uniforme."""
    total = await _count_total_dispatches_closed(db)
    if total < WARMUP_THRESHOLD:
        return random.choice(ARMS)

    x = features_to_vector(features)
    best_arm = None
    best_p = -1.0
    for arm in ARMS:
        mu, Sigma, _ = await _load_bandit_state(db, arm)
        try:
            w_sample = np.random.multivariate_normal(mu, Sigma)
        except np.linalg.LinAlgError:
            w_sample = mu + np.random.normal(0, PRIOR_SIGMA, size=mu.shape)
        p = float(_sigmoid(x @ w_sample))
        if p > best_p:
            best_p = p
            best_arm = arm
    return best_arm or ARMS[0]


# ----- Refit -----

async def refit_posterior(db) -> dict[str, Any]:
    """Refita o posterior de cada braço em cima dos dispatches fechados."""
    stats: dict[str, Any] = {}
    for arm in ARMS:
        cursor = await db.execute(
            """SELECT features_json, reward FROM rewarm_dispatches
               WHERE arm = ? AND closed_at IS NOT NULL AND reward IS NOT NULL""",
            (arm,),
        )
        rows = await cursor.fetchall()
        n = len(rows)
        if n == 0:
            continue

        feature_rows = [json.loads(r["features_json"]) for r in rows]
        X = np.array([features_to_vector(fr) for fr in feature_rows], dtype=float)
        y = np.array([int(r["reward"]) for r in rows], dtype=float)

        mu, Sigma = _laplace_fit(X, y)
        feature_names_json = json.dumps(list(FEATURE_NAMES))
        mu_json = json.dumps(mu.tolist())
        sigma_json = json.dumps(Sigma.flatten().tolist())

        await db.execute(
            """INSERT INTO bandit_state (arm, feature_names_json, mu_json, sigma_json, n_obs, updated_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(arm) DO UPDATE SET
                   feature_names_json=excluded.feature_names_json,
                   mu_json=excluded.mu_json,
                   sigma_json=excluded.sigma_json,
                   n_obs=excluded.n_obs,
                   updated_at=datetime('now')""",
            (arm, feature_names_json, mu_json, sigma_json, n),
        )
        stats[arm] = {"n_obs": n, "reward_rate": float(y.mean())}

    await db.commit()
    return stats


# ----- Slot datetime -----

def compute_slot_datetime(arm: str, anchor: datetime | None = None) -> datetime:
    """Retorna datetime tz-aware do slot no fuso local, com jitter uniforme em ±JITTER_MINUTES.

    Para persistir em scheduled_sends.send_at (que o scheduler compara com datetime('now') UTC),
    use `format_send_at_utc`.
    """
    if anchor is None:
        anchor = now_local()
    hour, minute = SLOT_HOURS[arm]
    base = anchor.replace(hour=hour, minute=minute, second=0, microsecond=0)
    jitter_seconds = random.uniform(-JITTER_MINUTES * 60, JITTER_MINUTES * 60)
    return base + timedelta(seconds=jitter_seconds)


def format_send_at_utc(dt: datetime) -> str:
    """Converte datetime tz-aware para string UTC que casa com datetime('now') do SQLite."""
    if dt.tzinfo is None:
        raise ValueError("format_send_at_utc requires tz-aware datetime")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ----- Response classification -----

async def classify_response_productive(conversation_id: int, since_iso: str) -> bool:
    """Chama Haiku para classificar se a resposta do lead foi produtiva."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT direction, content, sent_by, created_at
               FROM messages WHERE conversation_id = ? AND created_at >= ?
               ORDER BY created_at ASC, id ASC""",
            (conversation_id, since_iso),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    if not rows:
        return False

    lines = []
    for m in rows:
        tag = "cliente" if m["direction"] == "inbound" else f"operador ({m['sent_by'] or 'equipe'})"
        lines.append(f"[{m['created_at']}] {tag}: {m['content']}")
    history_text = "\n".join(lines)

    client = get_anthropic_client()
    response = await client.messages.create(
        model=settings.claude_haiku_model,
        max_tokens=512,
        system=PRODUCTIVE_SYSTEM_PROMPT,
        tools=[PRODUCTIVE_TOOL],
        tool_choice={"type": "tool", "name": PRODUCTIVE_TOOL_NAME},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Histórico após o toque de rewarm:\n\n{history_text}\n\n"
                    "A resposta do lead foi produtiva?"
                ),
            }
        ],
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == PRODUCTIVE_TOOL_NAME:
            inp = block.input or {}
            return bool(inp.get("productive", False))
    return False


# ----- Reward hook -----

async def handle_reward_inbound(conversation_id: int, inbound_msg_id: int) -> None:
    """Pós-webhook: se há dispatch aberto recente, classifica resposta e grava reward."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, sent_at FROM rewarm_dispatches
               WHERE conversation_id = ?
                 AND sent_at IS NOT NULL
                 AND responded_at IS NULL
                 AND closed_at IS NULL
                 AND datetime(sent_at) >= datetime('now', '-48 hours')
               ORDER BY sent_at DESC LIMIT 1""",
            (conversation_id,),
        )
        dispatch = await cursor.fetchone()
        if not dispatch:
            return
        dispatch_id = dispatch["id"]
        sent_at_iso = dispatch["sent_at"]

        msg_cursor = await db.execute(
            "SELECT created_at FROM messages WHERE id = ?",
            (inbound_msg_id,),
        )
        msg_row = await msg_cursor.fetchone()
        if not msg_row:
            return
        responded_at = msg_row["created_at"]
    finally:
        await db.close()

    try:
        productive = await classify_response_productive(conversation_id, sent_at_iso)
    except Exception as exc:  # noqa: BLE001
        logger.warning("rewarm reward classify failed conv=%s: %s", conversation_id, exc)
        return

    db = await get_db()
    try:
        await db.execute(
            """UPDATE rewarm_dispatches
               SET responded_at = ?,
                   productive = ?,
                   reward = ?,
                   closed_at = datetime('now'),
                   status = 'closed'
               WHERE id = ? AND responded_at IS NULL""",
            (responded_at, int(productive), int(productive), dispatch_id),
        )
        await db.commit()
        logger.info(
            "rewarm reward dispatch=%s conv=%s productive=%s",
            dispatch_id, conversation_id, productive,
        )
    finally:
        await db.close()


async def mark_dispatch_skipped_client_replied(db, scheduled_send_id: int) -> None:
    """Marcado quando webhook cancela scheduled_send por client_replied antes do envio."""
    await db.execute(
        """UPDATE rewarm_dispatches
           SET status = 'skipped_client_replied', closed_at = datetime('now')
           WHERE scheduled_send_id = ? AND status = 'pending' AND sent_at IS NULL""",
        (scheduled_send_id,),
    )


# ----- Closeout of stale dispatches -----

async def close_stale_dispatches(db) -> int:
    """Marca reward=0 em dispatches enviados há mais de 48h sem resposta."""
    cursor = await db.execute(
        """UPDATE rewarm_dispatches
           SET reward = 0,
               productive = 0,
               closed_at = datetime('now'),
               status = 'closed'
           WHERE sent_at IS NOT NULL
             AND responded_at IS NULL
             AND closed_at IS NULL
             AND datetime(sent_at) < datetime('now', '-48 hours')
           RETURNING id"""
    )
    closed = await cursor.fetchall()
    await db.commit()
    return len(closed)
