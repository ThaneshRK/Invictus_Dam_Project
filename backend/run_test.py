import httpx
import asyncio
import uuid
import os

async def main():
    async with httpx.AsyncClient(app=None, base_url="http://127.0.0.1:8000") as client:
        pass # Not easily callable outside.

