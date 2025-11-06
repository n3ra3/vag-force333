from fastapi import FastAPI
from .routers import router

app = FastAPI(title="payments-service")
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok"}
