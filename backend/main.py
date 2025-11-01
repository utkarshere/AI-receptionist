from fastapi import FastAPI
from .routes import test_db_routes, chat

app = FastAPI(
    title='AI Receptionist Assistant API',
    description='API for speedchain assignment',
)

# Include the main chat router (for the app)
app.include_router(chat.router, tags=["Chat"])

# Include the test routes
app.include_router(test_db_routes.router, prefix="/test", tags=["_TEST_Database"])

@app.get('/')
def read_root():
    return {'message': 'AI Receptionist Backend is running!'}