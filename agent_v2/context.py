"""
Shared context and state management for agents
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import time
import os
import polars as pl
from threading import Lock

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    agent: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def start(self):
        self.status = TaskStatus.RUNNING
        self.started_at = time.time()

    def complete(self, result: Any):
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = time.time()

    def fail(self, error: str):
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = time.time()

class SharedContext:
    """Thread-safe shared context for all agents"""

    def __init__(self):
        self._lock = Lock()
        self.tasks: Dict[str, Task] = {}
        self.dataframes: Dict[str, pl.DataFrame] = {}
        self.queries: Dict[str, str] = {}
        self.metadata: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, str]] = []
        self.errors: List[str] = []
        self.debug = os.getenv('DEBUG', '0') == '1'

    def log(self, message: str):
        """Debug logging"""
        if self.debug:
            print(f"[CONTEXT][{time.strftime('%H:%M:%S')}] {message}")

    def add_task(self, task_id: str, agent: str, description: str) -> Task:
        with self._lock:
            self.log(f"[ADD_TASK] Creating task {task_id} for agent {agent}")
            task = Task(id=task_id, agent=agent, description=description)
            self.tasks[task_id] = task
            self.log(f"[ADD_TASK] Task {task_id} added. Total tasks: {len(self.tasks)}")
            return task

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self.tasks.get(task_id)

    def update_task(self, task_id: str, status: TaskStatus, result: Any = None, error: str = None):
        with self._lock:
            if task_id in self.tasks:
                self.log(f"[UPDATE_TASK] Updating task {task_id} to status {status.value}")
                task = self.tasks[task_id]
                if status == TaskStatus.RUNNING:
                    task.start()
                    self.log(f"[UPDATE_TASK] Task {task_id} started")
                elif status == TaskStatus.COMPLETED:
                    task.complete(result)
                    self.log(f"[UPDATE_TASK] Task {task_id} completed with result: {str(result)[:100]}")
                elif status == TaskStatus.FAILED:
                    task.fail(error)
                    self.log(f"[UPDATE_TASK] Task {task_id} failed with error: {error}")
            else:
                self.log(f"[UPDATE_TASK-ERROR] Task {task_id} not found")

    def store_dataframe(self, key: str, df: pl.DataFrame):
        with self._lock:
            self.log(f"[STORE_DF] Storing DataFrame with key {key}, shape: {df.shape}")
            self.dataframes[key] = df
            self.log(f"[STORE_DF] Total DataFrames stored: {len(self.dataframes)}")

    def get_dataframe(self, key: str) -> Optional[pl.DataFrame]:
        with self._lock:
            return self.dataframes.get(key)

    def store_query(self, key: str, query: str):
        with self._lock:
            self.log(f"[STORE_QUERY] Storing query with key {key}, length: {len(query)}")
            self.log(f"[STORE_QUERY] Query preview: {query[:200]}...")
            self.queries[key] = query

    def add_error(self, error: str):
        with self._lock:
            timestamped_error = f"[{time.strftime('%H:%M:%S')}] {error}"
            self.log(f"[ADD_ERROR] Recording error: {error}")
            self.errors.append(timestamped_error)
            self.log(f"[ADD_ERROR] Total errors: {len(self.errors)}")

    def get_pending_tasks(self) -> List[Task]:
        with self._lock:
            return [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]

    def get_running_tasks(self) -> List[Task]:
        with self._lock:
            return [t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]

    def all_tasks_completed(self) -> bool:
        with self._lock:
            return all(t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
                      for t in self.tasks.values())

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_tasks": len(self.tasks),
                "completed": len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
                "failed": len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED]),
                "running": len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]),
                "pending": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
                "dataframes": list(self.dataframes.keys()),
                "errors": len(self.errors)
            }