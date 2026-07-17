"""Registro de background tasks fire-and-forget.

O event loop guarda apenas referência fraca às tasks; sem referência forte,
uma task em andamento pode ser coletada pelo GC antes de terminar. Este módulo
centraliza o padrão: spawn() cria a task, guarda referência forte em
PENDING_TASKS e a descarta via done-callback quando a task conclui.
"""

import asyncio
from collections.abc import Coroutine

PENDING_TASKS: set[asyncio.Task] = set()


def spawn(coro: Coroutine) -> asyncio.Task:
    """Cria a task e a mantém referenciada até concluir."""
    task = asyncio.create_task(coro)
    # Tasks órfãs de loops já fechados nunca vão concluir nem disparar callback
    for pending in list(PENDING_TASKS):
        if pending.done() or pending.get_loop().is_closed():
            PENDING_TASKS.discard(pending)
    PENDING_TASKS.add(task)
    task.add_done_callback(PENDING_TASKS.discard)
    return task
