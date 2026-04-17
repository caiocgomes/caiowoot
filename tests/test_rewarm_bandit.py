import json
from collections import Counter
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services import rewarm_bandit
from app.services.rewarm_bandit import (
    FEATURE_NAMES,
    PRODUCTIVE_TOOL_NAME,
    WARMUP_THRESHOLD,
    _laplace_fit,
    close_stale_dispatches,
    compute_slot_datetime,
    extract_features,
    features_to_vector,
    refit_posterior,
    sample_arm,
)


def _productive_resp(productive: bool, reason: str = "x"):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = PRODUCTIVE_TOOL_NAME
    block.input = {"productive": productive, "reason": reason}
    mock.content = [block]
    return mock


async def _seed_conv(db, phone="5511", stage="handbook_sent"):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES (?, 'X', 'curso-cdo', ?)",
        (phone, stage),
    )
    await db.commit()
    return cursor.lastrowid


@pytest.mark.asyncio
async def test_extract_features_no_history(db):
    conv_id = await _seed_conv(db, phone="5511", stage="handbook_sent")
    features = await extract_features(db, conv_id)
    assert features["has_history"] == 0.0
    assert features["hora_resp_tipica_utc"] == 0.0
    assert features["estagio_link"] == 0.0
    assert features["intercept"] == 1.0


@pytest.mark.asyncio
async def test_extract_features_with_inbound_history(db):
    conv_id = await _seed_conv(db, phone="5512", stage="link_sent")
    # 10h, 14h, 18h → mediana 14h
    for ts in ("2026-04-10 10:00:00", "2026-04-11 14:00:00", "2026-04-12 18:00:00"):
        await db.execute(
            "INSERT INTO messages (conversation_id, direction, content, created_at) "
            "VALUES (?, 'inbound', 'oi', ?)",
            (conv_id, ts),
        )
    await db.commit()
    features = await extract_features(db, conv_id)
    assert features["has_history"] == 1.0
    assert features["hora_resp_tipica_utc"] == 14.0
    assert features["estagio_link"] == 1.0


@pytest.mark.asyncio
async def test_sample_arm_warmup_is_roughly_balanced(db):
    features = {
        "intercept": 1.0,
        "has_history": 0.0,
        "hora_resp_tipica_utc": 0.0,
        "estagio_link": 0.0,
    }
    counts = Counter()
    for _ in range(200):
        arm = await sample_arm(db, features)
        counts[arm] += 1
    # Em warmup com <40 dispatches fechados, é 50/50 uniforme.
    assert 70 <= counts["noon"] <= 130
    assert 70 <= counts["evening"] <= 130


@pytest.mark.asyncio
async def test_sample_arm_thompson_prefers_better_arm_after_warmup(db):
    # Seeds 50 dispatches fechados: "evening" com reward 1 sempre, "noon" com reward 0 sempre.
    features = {
        "intercept": 1.0,
        "has_history": 0.0,
        "hora_resp_tipica_utc": 12.0,
        "estagio_link": 0.0,
    }
    features_json = json.dumps(features)
    conv_id = await _seed_conv(db, phone="5599", stage="handbook_sent")
    for i in range(25):
        await db.execute(
            """INSERT INTO rewarm_dispatches
               (conversation_id, features_json, arm, scheduled_for, sent_at, responded_at, productive, reward, closed_at, status)
               VALUES (?, ?, 'evening', '2026-04-01 18:30:00', '2026-04-01 18:30:00', '2026-04-01 18:50:00', 1, 1, '2026-04-01 19:00:00', 'closed')""",
            (conv_id, features_json),
        )
    for i in range(25):
        await db.execute(
            """INSERT INTO rewarm_dispatches
               (conversation_id, features_json, arm, scheduled_for, sent_at, responded_at, productive, reward, closed_at, status)
               VALUES (?, ?, 'noon', '2026-04-01 12:30:00', '2026-04-01 12:30:00', NULL, 0, 0, '2026-04-01 15:00:00', 'closed')""",
            (conv_id, features_json),
        )
    await db.commit()

    # Refita posterior para cada braço
    await refit_posterior(db)

    # Sample 200x, evening tem que dominar
    counts = Counter()
    for _ in range(200):
        counts[await sample_arm(db, features)] += 1

    assert counts["evening"] > counts["noon"] * 2


@pytest.mark.asyncio
async def test_laplace_fit_produces_reasonable_posterior():
    # Dataset sintético com efeito forte
    rng = np.random.default_rng(42)
    n = 200
    X = np.hstack([np.ones((n, 1)), rng.normal(size=(n, 3))])
    true_w = np.array([-0.5, 2.0, 0.0, 0.0])
    probs = 1.0 / (1.0 + np.exp(-X @ true_w))
    y = (rng.uniform(size=n) < probs).astype(float)

    mu, Sigma = _laplace_fit(X, y)
    # Sinal do coeficiente 1 deve ser positivo (forte)
    assert mu[1] > 0.5
    # Matriz de covariância positiva definida
    eigs = np.linalg.eigvalsh(Sigma)
    assert np.all(eigs > 0)


@pytest.mark.asyncio
async def test_refit_posterior_is_noop_without_data(db):
    stats = await refit_posterior(db)
    assert stats == {}


@pytest.mark.asyncio
async def test_classify_response_productive_returns_true(db):
    conv_id = await _seed_conv(db, phone="5531")
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) "
        "VALUES (?, 'inbound', 'mas quanto custa o curso?', '2026-04-15 14:00:00')",
        (conv_id,),
    )
    await db.commit()

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_productive_resp(True))
    with patch("app.services.rewarm_bandit.get_anthropic_client", return_value=mock_client):
        result = await rewarm_bandit.classify_response_productive(conv_id, "2026-04-15 13:00:00")
    assert result is True


@pytest.mark.asyncio
async def test_classify_response_productive_returns_false_on_empty(db):
    conv_id = await _seed_conv(db, phone="5532")
    mock_client = AsyncMock()
    with patch("app.services.rewarm_bandit.get_anthropic_client", return_value=mock_client):
        result = await rewarm_bandit.classify_response_productive(conv_id, "2026-04-15 13:00:00")
    assert result is False
    # Sem histórico, não chama Haiku
    mock_client.messages.create.assert_not_called()


@pytest.mark.asyncio
async def test_close_stale_dispatches_marks_old_as_reward_zero(db):
    conv_id = await _seed_conv(db, phone="5533")
    features_json = json.dumps({name: 0.0 for name in FEATURE_NAMES})

    # Um stale (sent há 50h), outro fresh (sent há 2h)
    await db.execute(
        """INSERT INTO rewarm_dispatches
           (conversation_id, features_json, arm, scheduled_for, sent_at, status)
           VALUES (?, ?, 'noon', '2026-01-01 12:30:00', datetime('now','-50 hours'), 'sent')""",
        (conv_id, features_json),
    )
    await db.execute(
        """INSERT INTO rewarm_dispatches
           (conversation_id, features_json, arm, scheduled_for, sent_at, status)
           VALUES (?, ?, 'evening', '2026-01-01 18:30:00', datetime('now','-2 hours'), 'sent')""",
        (conv_id, features_json),
    )
    await db.commit()

    closed = await close_stale_dispatches(db)
    assert closed == 1

    cursor = await db.execute("SELECT reward, productive, status FROM rewarm_dispatches WHERE arm='noon'")
    row = await cursor.fetchone()
    assert row["reward"] == 0
    assert row["productive"] == 0
    assert row["status"] == "closed"

    cursor = await db.execute("SELECT reward, status FROM rewarm_dispatches WHERE arm='evening'")
    row = await cursor.fetchone()
    assert row["reward"] is None
    assert row["status"] == "sent"


def test_compute_slot_datetime_respects_arm():
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo
    anchor = _dt(2026, 4, 17, 9, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    noon = compute_slot_datetime("noon", anchor)
    evening = compute_slot_datetime("evening", anchor)
    assert 12 <= noon.hour <= 13 or (noon.hour == 12 and noon.minute >= 15)
    assert 18 <= evening.hour <= 19 or (evening.hour == 18 and evening.minute >= 15)
    assert noon.date() == anchor.date()


def test_format_send_at_utc_converts_local_to_utc():
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo
    from app.services.rewarm_bandit import format_send_at_utc
    local_1230 = _dt(2026, 4, 17, 12, 30, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert format_send_at_utc(local_1230) == "2026-04-17 15:30:00"
    local_1830 = _dt(2026, 4, 17, 18, 30, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert format_send_at_utc(local_1830) == "2026-04-17 21:30:00"


def test_format_send_at_utc_rejects_naive():
    from datetime import datetime as _dt
    from app.services.rewarm_bandit import format_send_at_utc
    with pytest.raises(ValueError):
        format_send_at_utc(_dt(2026, 4, 17, 12, 30, 0))


def test_features_to_vector_order():
    features = {
        "intercept": 1.0,
        "has_history": 1.0,
        "hora_resp_tipica_utc": 12.5,
        "estagio_link": 0.0,
    }
    vec = features_to_vector(features)
    assert list(vec) == [1.0, 1.0, 12.5, 0.0]
