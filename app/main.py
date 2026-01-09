#run app: uvicorn app.main:app --reload
from fastapi import FastAPI
from app.api.optimizator import optimizator

app = FastAPI()
app.include_router(optimizator, prefix="/optimizacije")

