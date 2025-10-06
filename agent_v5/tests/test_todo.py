"""
Tests for TodoWrite tool
"""
import pytest
from agent_v5.tools.todo import TodoWriteTool


@pytest.mark.asyncio
async def test_todo_empty_list():
    """Test 1: Initialize with no todos"""
    tool = TodoWriteTool("/workspace")

    result = await tool.execute({"todos": []})

    assert result["is_error"] is False
    assert len(tool.todos) == 0


@pytest.mark.asyncio
async def test_todo_add_tasks():
    """Test 2: Add pending tasks"""
    tool = TodoWriteTool("/workspace")

    todos = [
        {"content": "Task 1", "activeForm": "Working on Task 1", "status": "pending"},
        {"content": "Task 2", "activeForm": "Working on Task 2", "status": "pending"}
    ]

    result = await tool.execute({"todos": todos})

    assert result["is_error"] is False
    assert len(tool.todos) == 2
    assert tool.todos[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_todo_mark_in_progress():
    """Test 3: One task in progress"""
    tool = TodoWriteTool("/workspace")

    todos = [
        {"content": "Task 1", "activeForm": "Working on Task 1", "status": "in_progress"},
        {"content": "Task 2", "activeForm": "Working on Task 2", "status": "pending"}
    ]

    result = await tool.execute({"todos": todos})

    assert result["is_error"] is False
    in_progress = [t for t in tool.todos if t["status"] == "in_progress"]
    assert len(in_progress) == 1


@pytest.mark.asyncio
async def test_todo_multiple_in_progress_warning():
    """Test 4: Warning when multiple tasks in progress"""
    tool = TodoWriteTool("/workspace")

    todos = [
        {"content": "Task 1", "activeForm": "Working on Task 1", "status": "in_progress"},
        {"content": "Task 2", "activeForm": "Working on Task 2", "status": "in_progress"}
    ]

    result = await tool.execute({"todos": todos})

    assert result["is_error"] is False
    assert "Warning" in result["content"]
    assert "More than one" in result["content"]


@pytest.mark.asyncio
async def test_todo_complete_task():
    """Test 5: Mark task as completed"""
    tool = TodoWriteTool("/workspace")

    todos = [
        {"content": "Task 1", "activeForm": "Working on Task 1", "status": "completed"},
        {"content": "Task 2", "activeForm": "Working on Task 2", "status": "pending"}
    ]

    result = await tool.execute({"todos": todos})

    assert result["is_error"] is False
    completed = [t for t in tool.todos if t["status"] == "completed"]
    assert len(completed) == 1


@pytest.mark.asyncio
async def test_todo_required_fields():
    """Test 6: All required fields are present"""
    tool = TodoWriteTool("/workspace")

    todos = [
        {"content": "Task 1", "activeForm": "Working on Task 1", "status": "pending"}
    ]

    result = await tool.execute({"todos": todos})

    assert result["is_error"] is False
    assert tool.todos[0]["content"] == "Task 1"
    assert tool.todos[0]["activeForm"] == "Working on Task 1"
    assert tool.todos[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_todo_status_values():
    """Test 7: All valid status values work"""
    tool = TodoWriteTool("/workspace")

    todos = [
        {"content": "T1", "activeForm": "A1", "status": "pending"},
        {"content": "T2", "activeForm": "A2", "status": "in_progress"},
        {"content": "T3", "activeForm": "A3", "status": "completed"}
    ]

    result = await tool.execute({"todos": todos})

    assert result["is_error"] is False
    assert tool.todos[0]["status"] == "pending"
    assert tool.todos[1]["status"] == "in_progress"
    assert tool.todos[2]["status"] == "completed"


@pytest.mark.asyncio
async def test_todo_updates_list():
    """Test 8: TodoWrite updates the internal list"""
    tool = TodoWriteTool("/workspace")

    todos1 = [{"content": "Task 1", "activeForm": "A1", "status": "pending"}]
    await tool.execute({"todos": todos1})
    assert len(tool.todos) == 1

    todos2 = [
        {"content": "Task 1", "activeForm": "A1", "status": "completed"},
        {"content": "Task 2", "activeForm": "A2", "status": "pending"}
    ]
    await tool.execute({"todos": todos2})
    assert len(tool.todos) == 2
    assert tool.todos[0]["status"] == "completed"
