from __future__ import annotations

import asyncio
import json

import redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings

router = APIRouter(tags=["ws"])
redis_client = redis.Redis.from_url(settings.REDIS_URL)


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_ws(websocket: WebSocket, task_id: str) -> None:
    await websocket.accept()
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    channel = f"task:{task_id}"
    pubsub.subscribe(channel)

    try:
        while True:
            message = pubsub.get_message(timeout=1.0)
            if message and message.get("type") == "message":
                raw_data = message.get("data")
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode("utf-8")
                payload = json.loads(raw_data)
                await websocket.send_json(payload)

                if payload.get("status") in {"completed", "failed", "canceled"}:
                    break
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        pubsub.close()
