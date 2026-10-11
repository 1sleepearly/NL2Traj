"""Small OpenAI-compatible model and PostgreSQL adapters."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import psycopg2
import requests


@dataclass
class ChatModel:
    """OpenAI-compatible chat-completions client configured by an env prefix."""

    env_prefix: str

    def __post_init__(self) -> None:
        prefix = self.env_prefix.upper()
        self.api_key = os.getenv(f"{prefix}_API_KEY")
        self.api_url = os.getenv(f"{prefix}_API_URL")
        self.model = os.getenv(f"{prefix}_MODEL")
        if not all((self.api_key, self.api_url, self.model)):
            raise ValueError(f"Set {prefix}_API_KEY, {prefix}_API_URL, and {prefix}_MODEL")

    def generate(self, prompt: str, system_prompt: str, temperature: float = 0.1) -> str:
        response = requests.post(
            self.api_url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


def execute_read_only(sql: str) -> str:
    """Execute one read-only statement and return rows as JSON."""
    if not sql.lstrip().lower().startswith(("select", "with")):
        raise ValueError("only SELECT or WITH statements are allowed")
    connection = psycopg2.connect(
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=int(os.getenv("DATABASE_PORT", "5432")),
        dbname=os.environ["DATABASE_NAME"],
        user=os.environ["DATABASE_USER"],
        password=os.environ["DATABASE_PASSWORD"],
        options="-c default_transaction_read_only=on -c statement_timeout=30000",
    )
    try:
        with connection, connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        return json.dumps(rows, ensure_ascii=False, default=str)
    finally:
        connection.close()

