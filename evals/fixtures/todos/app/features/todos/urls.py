from stario import Route

TODOS = Route("GET /todos")
TODOS_LIVE = Route("GET /todos/live")
ADD_TODO = Route("POST /todos")
TOGGLE_TODO = Route("POST /todos/{todo_id}/toggle")
