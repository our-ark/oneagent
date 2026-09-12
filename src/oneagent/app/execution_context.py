from __future__ import annotations

from contextvars import ContextVar

from oneagent.app.models import WorkStatusMessage
from oneagent.prompt_append import TaskRegressionSignal


CURRENT_WORK_STATUS: ContextVar[WorkStatusMessage | None] = ContextVar(
    "oneagent_work_status",
    default=None,
)
CURRENT_TASK_ID: ContextVar[int | None] = ContextVar("oneagent_task_id", default=None)
CURRENT_TASK_WORKER_ID: ContextVar[str] = ContextVar(
    "oneagent_task_worker_id",
    default="",
)
CURRENT_REGRESSION_SIGNALS: ContextVar[tuple[TaskRegressionSignal, ...]] = ContextVar(
    "oneagent_regression_signals",
    default=(),
)
