from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="Content Creation Platform",
    description="AI-powered content creation for multiple client agencies",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Content Creation Platform API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)