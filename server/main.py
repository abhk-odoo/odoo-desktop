import sys
import atexit
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.root import router as root_router
from routes.printer import router as printer_router
from routes.zebra import router as zebra_router
from services.printer_service import printer_shutdown

app = FastAPI(title="Local Print Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root_router)
app.include_router(printer_router)
app.include_router(zebra_router)

def shutdown_event():
    printer_shutdown()

if __name__ == "__main__":
    atexit.register(shutdown_event)

    port = 5050
    for arg in sys.argv:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])

    uvicorn.run(app, host="127.0.0.1", port=port)
