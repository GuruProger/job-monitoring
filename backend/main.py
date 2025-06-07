import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import router as api_router

app = FastAPI()
app.include_router(api_router)

# app.add_middleware(
# 	CORSMiddleware,
# 	allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
# 	allow_credentials=True,
# 	allow_methods=["*"],
# 	allow_headers=["*"],
# )

if __name__ == "__main__":
	uvicorn.run(
		app,
		host='127.0.0.1',
		port=8000,
	)
