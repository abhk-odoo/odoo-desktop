import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.printer import router as printer_router
from routes.root import router as root_router
from routes.zebra import router as zebra_router
from services.printer_service_usb import shutdown_usb_printer_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # cleanup code
    shutdown_usb_printer_services()


app = FastAPI(title="Local Print Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root_router)
app.include_router(printer_router)
app.include_router(zebra_router)


if __name__ == "__main__":
    port = 5050
    for arg in sys.argv:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])

    uvicorn.run(app, host="127.0.0.1", port=port)
