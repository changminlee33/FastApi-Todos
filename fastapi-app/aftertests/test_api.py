import requests

BASE_URL = "http://43.201.68.233:8002/"

def test_get_todos_empty():
    response = requests.get(f"{BASE_URL}/todos")
    assert response.status_code == 200
    assert response.json() == []

def test_create_todo():
    todo = {"id": 1, "title": "Test", "description": "Test description", "completed": False}
    response = requests.post(f"{BASE_URL}/todos", json=todo)
    assert response.status_code == 200
    assert response.json()["title"] == "Test"

def test_get_todos_with_items():
    response = requests.get(f"{BASE_URL}/todos")
    assert response.status_code == 200
    todos = response.json()
    assert len(todos) >= 1
    assert any(todo["title"] == "Test" for todo in todos)

def test_create_todo_invalid():
    todo = {"id": 1, "title": "Test"}  # description, completed 없음
    response = requests.post(f"{BASE_URL}/todos", json=todo)
    assert response.status_code == 422

def test_update_todo():
    updated_todo = {
        "id": 1,
        "title": "Updated",
        "description": "Updated description",
        "completed": True
    }
    response = requests.put(f"{BASE_URL}/todos/1", json=updated_todo)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"

def test_update_todo_not_found():
    updated_todo = {
        "id": 999,
        "title": "Nope",
        "description": "Should not exist",
        "completed": True
    }
    response = requests.put(f"{BASE_URL}/todos/999", json=updated_todo)
    assert response.status_code == 404

def test_delete_todo():
    response = requests.delete(f"{BASE_URL}/todos/1")
    assert response.status_code == 200
    assert response.json()["message"] == "To-Do item deleted"

def test_delete_todo_not_found():
    response = requests.delete(f"{BASE_URL}/todos/999")
    assert response.status_code == 404
    assert response.json()["message"] == "To-Do item not found"
