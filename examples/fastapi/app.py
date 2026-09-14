#!/usr/bin/env python
"""Small FastAPI/WebSocket demo around a Sllurp LLRP reader."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from queue import Empty, Full, Queue

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.websockets import WebSocket, WebSocketDisconnect

from sllurp.llrp import (
    LLRP_DEFAULT_PORT,
    LLRPReaderClient,
    LLRPReaderConfig,
    LLRPReaderState,
)

logger = logging.getLogger("sllurp.fastapi_demo")


class RFIDTag(BaseModel):
    epc: str
    channel: int
    last_seen: int
    seen_count: int


READER_HOST = os.getenv("SLLURP_READER_HOST", "localhost")
READER_PORT = int(os.getenv("SLLURP_READER_PORT", str(LLRP_DEFAULT_PORT)))
WEB_HOST = os.getenv("SLLURP_WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("SLLURP_WEB_PORT", "4000"))
INDEX_PATH = Path(__file__).with_name("index.html")

READER: LLRPReaderClient | None = None
TAG_DATA: list[RFIDTag] = []
# WebSocket clients only need the newest observation batch. Keeping a single
# pending batch prevents a slow client from causing unbounded queue growth.
TAG_QUEUE: Queue = Queue(maxsize=1)
ACTIVE_CONNECTIONS: set[WebSocket] = set()


def _publish_latest_tags(tags):
    """Queue the newest tag batch, replacing an older unsent batch if needed."""
    while True:
        try:
            TAG_QUEUE.put_nowait(tags)
            return
        except Full:
            try:
                TAG_QUEUE.get_nowait()
            except Empty:
                continue


async def process_queue():
    while True:
        try:
            tags = TAG_QUEUE.get_nowait()
        except Empty:
            await asyncio.sleep(0.1)
            continue

        stale_connections = []
        for connection in tuple(ACTIVE_CONNECTIONS):
            try:
                await connection.send_json({"tags": tags})
            except Exception:
                logger.exception("Error sending tags to WebSocket client")
                stale_connections.append(connection)
        for connection in stale_connections:
            ACTIVE_CONNECTIONS.discard(connection)


@asynccontextmanager
async def lifespan(_application: FastAPI):
    global READER
    config = LLRPReaderConfig(
        {
            "reset_on_connect": True,
            "start_inventory": False,
            "event_selector": {"GPIEvent": True},
        }
    )
    READER = LLRPReaderClient(READER_HOST, READER_PORT, config)
    READER.add_tag_report_callback(tag_report_cb)
    READER.add_event_callback(handle_event)
    READER.connect()
    logger.info("Connected to RFID reader %s:%s", READER_HOST, READER_PORT)

    task = asyncio.create_task(process_queue())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        if READER and READER.is_alive():
            try:
                READER.disconnect(timeout=2)
                if READER.is_alive():
                    READER.hard_disconnect()
                    READER.join(1)
            except Exception:
                logger.exception("Error during reader shutdown")
                READER.hard_disconnect()


app = FastAPI(lifespan=lifespan)
logging.basicConfig(level=logging.INFO)


def _epc_text(value):
    if isinstance(value, bytes):
        return value.decode("ascii", errors="replace")
    return str(value)


def tag_report_cb(_reader, tag_reports):
    global TAG_DATA
    TAG_DATA = [
        RFIDTag(
            epc=_epc_text(tag.get("EPC", "")),
            channel=int(tag.get("ChannelIndex", 0)),
            last_seen=int(tag.get("LastSeenTimestampUTC", 0)),
            seen_count=int(tag.get("TagSeenCount", 0)),
        )
        for tag in tag_reports
    ]
    _publish_latest_tags([tag.model_dump() for tag in TAG_DATA])
    logger.info("Received %d tag reports", len(tag_reports))


def handle_event(_reader, event):
    gpi_event = event.get("GPIEvent")
    if gpi_event and gpi_event.get("GPIPortNumber") == 1:
        if gpi_event.get("GPIEvent"):
            start_reading()
        else:
            stop_reading()
    logger.debug("Reader event: %s", event)


def clear_tag_data():
    global TAG_DATA
    TAG_DATA = []


def start_reading():
    if READER and READER.is_alive():
        clear_tag_data()
        READER.llrp.startInventory()
        return True
    return False


def stop_reading():
    if READER and READER.is_alive():
        READER.llrp.stopPolitely()
        return True
    return False


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(INDEX_PATH)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ACTIVE_CONNECTIONS.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ACTIVE_CONNECTIONS.discard(websocket)


@app.post("/start")
async def start():
    return {"started": start_reading()}


@app.post("/stop")
async def stop():
    return {"stopped": stop_reading()}


@app.post("/start-stop")
async def start_stop():
    started = start_reading()
    if started:
        await asyncio.sleep(1)
    stopped = stop_reading()
    return {"started": started, "stopped": stopped}


@app.get("/last-read")
async def get_tags():
    return {"tags": [tag.model_dump() for tag in TAG_DATA]}


@app.get("/status")
async def status():
    return {"connected": bool(READER and READER.is_alive())}


@app.get("/state")
async def state():
    if READER is None:
        return {"state": "not-initialized", "code": None}
    return {
        "state": LLRPReaderState.getStateName(READER.llrp.state),
        "code": READER.llrp.state,
    }


@app.post("/clear")
async def clear():
    clear_tag_data()
    return {"message": "Tag data cleared"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT)
