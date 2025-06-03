from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json
import os
from fastapi.staticfiles import StaticFiles
from fastapi import Query
from prometheus_fastapi_instrumentator import Instrumentator
import logging
import time
from multiprocessing import Queue
from os import getenv
from fastapi import Request
from logging_loki import LokiQueueHandler

app = FastAPI()

# Prometheus 메트릭스 엔드포인트 (/metrics)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

loki_logs_handler = LokiQueueHandler(
    Queue(-1),
    url=getenv("LOKI_ENDPOINT"),
    tags={"application": "fastapi"},
    version="1",
)

# Custom access logger (ignore Uvicorn's default logging)
custom_logger = logging.getLogger("custom.access")
custom_logger.setLevel(logging.INFO)

# Add Loki handler (assuming `loki_logs_handler` is correctly configured)
custom_logger.addHandler(loki_logs_handler)

async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time  # Compute response time

    log_message = (
        f'{request.client.host} - "{request.method} {request.url.path} HTTP/1.1" {response.status_code} {duration:.3f}s'
    )

    # **Only log if duration exists**
    if duration:
        custom_logger.info(log_message)

    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 현재 파일 위치 기준 절대 경로 설정
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# To-Do 항목 모델
class TodoItem(BaseModel):
    id: int
    title: str
    description: str
    completed: bool
    priority: str = "medium"

# JSON 파일 경로
TODO_FILE = "todo.json"

# JSON 파일에서 To-Do 항목 로드
def load_todos():
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []
    return []

# JSON 파일에 To-Do 항목 저장
def save_todos(todos):
    with open(TODO_FILE, "w") as file:
        json.dump(todos, file, indent=4)
        
@app.get("/todos/priority/{level}", response_model=list[dict])
def get_todos_by_priority(level: str):
    todos = load_todos()
    level = level.lower()
    if level not in ["low", "medium", "high"]:
        raise HTTPException(status_code=400, detail="Invalid priority level")
    return [todo for todo in todos if todo.get("priority", "medium").lower() == level]

# To-Do 목록 조회
@app.get("/todos", response_model=list[dict])
def get_todos():
    return load_todos()

# 신규 To-Do 항목 추가 (자동 증가 ID 적용)
@app.post("/todos", response_model=dict)
def create_todo(todo: TodoItem):
    todos = load_todos()
    new_id = max([t["id"] for t in todos], default=0) + 1  # ID 자동 증가
    new_todo = {"id": new_id, **todo.dict()}
    todos.append(new_todo)
    save_todos(todos)
    return new_todo

# To-Do 항목 수정
@app.put("/todos/{todo_id}", response_model=dict)
def update_todo(todo_id: int, updated_todo: TodoItem):
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo.update(updated_todo.dict())
            save_todos(todos)
            return todo
    raise HTTPException(status_code=404, detail="To-Do item not found")

# To-Do 항목 삭제
@app.delete("/todos/{todo_id}", response_model=dict)
def delete_todo(todo_id: int):
    todos = load_todos()
    updated_todos = [todo for todo in todos if todo["id"] != todo_id]
    if len(updated_todos) == len(todos):
        raise HTTPException(status_code=404, detail="To-Do item not found")
    save_todos(updated_todos)
    return {"message": "To-Do item deleted"}

@app.get("/todos/completed", response_model = list[dict])
def get_completed_todos():
    todos = load_todos()
    lists = []
    for todo in todos:
        if todo["completed"] == True:
            lists.append(todo)
    return lists

@app.get("/todos/notcompleted", response_model = list[dict])
def get_not_completed_todos():
    todos = load_todos()
    lists = []
    for todo in todos:
        if todo["completed"] == False:
            lists.append(todo)
    return lists


@app.get("/todos/search", response_model=list[dict])
def search_todos(keyword: str = Query(..., description="검색할 키워드")):
    todos = load_todos()
    matched = [
        todo for todo in todos
        if keyword.lower() in todo["title"].lower() or keyword.lower() in todo["description"].lower()
    ]
    return matched

# To-Do 항목을 완료 처리
@app.patch("/todos/{todo_id}/complete", response_model=dict)
def complete_todo(todo_id: int):
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["completed"] = True
            save_todos(todos)
            return todo
    raise HTTPException(status_code=404, detail="To-Do item not found")

# To-Do 항목을 미완료 처리
@app.patch("/todos/{todo_id}/uncomplete", response_model=dict)
def uncomplete_todo(todo_id: int):
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["completed"] = False
            save_todos(todos)
            return todo
    raise HTTPException(status_code=404, detail="To-Do item not found")


@app.get("/")
def read_root():
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)
