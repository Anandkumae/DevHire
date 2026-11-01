import asyncio
import json
import logging
from typing import Any
from fastapi import WebSocket
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("devhire.notifications")


class ConnectionManager:
    """Manages active user WebSocket sessions and broadcasts notifications."""

    def __init__(self):
        self._active_connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._redis: aioredis.Redis | None = None
        self._listener_task: asyncio.Task | None = None

    async def get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
        return self._redis

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            if user_id not in self._active_connections:
                self._active_connections[user_id] = set()
            self._active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected: user {user_id} (active: {len(self._active_connections[user_id])})")

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if user_id in self._active_connections:
                self._active_connections[user_id].discard(websocket)
                if not self._active_connections[user_id]:
                    del self._active_connections[user_id]
        logger.info(f"WebSocket disconnected: user {user_id}")

    async def send_to_user_local(self, user_id: str, message: dict[str, Any]) -> None:
        """Sends payload to all connected local WebSockets of a given user."""
        async with self._lock:
            sockets = list(self._active_connections.get(user_id, []))

        dead_sockets = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending to WebSocket for user {user_id}: {e}")
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for ws in dead_sockets:
                    if user_id in self._active_connections:
                        self._active_connections[user_id].discard(ws)

    async def publish(self, user_id: str, payload: dict[str, Any]) -> None:
        """Publishes notification through Redis Pub/Sub and routes to local WebSockets."""
        # 1. Immediate local dispatch
        await self.send_to_user_local(user_id, payload)

        # 2. Redis Pub/Sub for multi-worker horizontal scalability
        try:
            r = await self.get_redis()
            channel = f"notifications:{user_id}"
            await r.publish(channel, json.dumps(payload))
        except Exception as exc:
            logger.warning(f"Redis publish failed: {exc}")

    async def start_listener(self) -> None:
        """Background listener subscribing to Redis pub/sub channels."""
        try:
            r = await self.get_redis()
            pubsub = r.pubsub()
            await pubsub.psubscribe("notifications:*")

            async def _listen():
                try:
                    async for message in pubsub.listen():
                        if message and message.get("type") == "pmessage":
                            channel = message.get("channel", "")
                            user_id = channel.split(":")[-1]
                            data_str = message.get("data", "{}")
                            try:
                                data = json.loads(data_str)
                                await self.send_to_user_local(user_id, data)
                            except Exception:
                                pass
                except asyncio.CancelledError:
                    await pubsub.close()
                except Exception as e:
                    logger.warning(f"Redis listener encountered error: {e}")

            self._listener_task = asyncio.create_task(_listen())
        except Exception as exc:
            logger.warning(f"Failed to start Redis notification listener: {exc}")

    async def stop_listener(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.close()


ws_manager = ConnectionManager()

