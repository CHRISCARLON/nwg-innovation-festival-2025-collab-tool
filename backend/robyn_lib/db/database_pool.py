from typing import List, Optional, AsyncGenerator
import asyncio
import duckdb
from loguru import logger
import os
from contextlib import asynccontextmanager


class MotherDuckPool:
    """A simple connection pool for MotherDuck with a maximum of 5 connections"""

    _instance: Optional["MotherDuckPool"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "initialized"):
            self.database = os.getenv("MD_DB")
            self.token = os.getenv("MD_TOKEN")

            if not all([self.database, self.token]):
                raise ValueError("MotherDuck environment variables are not present")

            self.connection_string = f"md:{self.database}?motherduck_token={self.token}&access_mode=read_only"
            self._connections: List[duckdb.DuckDBPyConnection] = []
            self._max_connections = 5
            self._lock = asyncio.Lock()
            self.initialized = True

    async def _create_connection(self) -> duckdb.DuckDBPyConnection:
        """Create a new MotherDuck connection"""
        try:
            conn = await asyncio.to_thread(duckdb.connect, self.connection_string)
            logger.debug("Created new MotherDuck connection")
            return conn
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[duckdb.DuckDBPyConnection, None]:
        """Get a connection from the pool or create a new one if available"""
        async with self._lock:
            if self._connections:
                connection = self._connections.pop()
                logger.debug("Reusing existing connection")
            elif len(self._connections) < self._max_connections:
                connection = await self._create_connection()
            else:
                logger.warning("Max connections reached, waiting...")
                while not self._connections:
                    await asyncio.sleep(0.2)
                connection = self._connections.pop()

        try:
            # Verify connection is still valid
            await asyncio.to_thread(connection.execute, "SELECT 1")
            yield connection

            # Return connection to pool
            async with self._lock:
                self._connections.append(connection)
                logger.debug("Returned connection to pool")

        except Exception as e:
            logger.error(f"Connection error: {e}")
            await asyncio.to_thread(connection.close)
            raise

    async def close_all(self):
        """Close all connections in the pool"""
        async with self._lock:
            while self._connections:
                conn = self._connections.pop()
                await asyncio.to_thread(conn.close)
            logger.info("Closed all connections in pool")
