import json
import requests
import time
import logging
import psycopg2
import os
import sys
import re
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class LLMResponseError(RuntimeError):
    """Raised when the model provider fails before producing a usable answer."""

class DatabaseConnectionError(RuntimeError):
    """Raised when the database is unavailable, not when a generated SQL is wrong."""

def _parse_chat_completion_response(response):
    """Parse normal JSON or PackyAPI SSE chat completion responses."""
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" not in content_type:
        return response.json()["choices"][0]["message"]["content"].strip()

    chunks = []
    # SSE proxies often omit ``charset=utf-8``.  ``requests.response.text``
    # then falls back to Latin-1 and corrupts Chinese content into mojibake.
    # Chat-completion JSON/SSE is UTF-8 by contract, so decode bytes explicitly.
    event_text = response.content.decode("utf-8")
    for raw_line in event_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            item = json.loads(payload)
        except ValueError:
            continue
        for choice in item.get("choices", []):
            delta = choice.get("delta") or {}
            message = choice.get("message") or {}
            piece = delta.get("content") or message.get("content") or ""
            if piece:
                chunks.append(piece)
    return "".join(chunks).strip()

def _is_non_retryable_api_error(status_code: int, api_err) -> bool:
    """Return True for provider errors that will not be fixed by retrying."""
    text = json.dumps(api_err, ensure_ascii=False) if isinstance(api_err, (dict, list)) else str(api_err)
    # Capacity/routing failures are transient even when a proxy labels them
    # HTTP 400; keep them in the retry path.
    if any(marker in text.lower() for marker in ("at capacity", "try a different model", "capacity")):
        return False
    markers = [
        "model_not_found",
        "resource_not_found_error",
        "invalid_request_error",
        "model is not supported",
        "does not exist",
        "Incorrect API key",
        "invalid api key",
        "Unauthorized",
    ]
    return status_code in {400, 401, 403, 404} and any(marker.lower() in text.lower() for marker in markers)


def _summarize_api_error(api_err, limit: int = 500) -> str:
    """Keep provider error logs readable, especially for proxy HTML pages."""
    if isinstance(api_err, (dict, list)):
        text = json.dumps(api_err, ensure_ascii=False)
    else:
        text = str(api_err)
    if "<html" in text.lower() or "<!doctype html" in text.lower():
        title = re.search(r"<title>\s*(.*?)\s*</title>", text, re.I | re.S)
        heading = re.search(r"Error code\s*(\d{3})", text, re.I)
        parts = ["HTML error page omitted"]
        if title:
            parts.append(re.sub(r"\s+", " ", title.group(1)).strip())
        if heading:
            parts.append(f"error_code={heading.group(1)}")
        return "; ".join(parts)
    compact = re.sub(r"\s+", " ", text).strip()
    return compact if len(compact) <= limit else compact[:limit] + "... [truncated]"

class UnifiedLLM:
    """统一模型调用接口，支持 Kimi、DeepSeek 和 GPT（PackyAPI 代理）"""
    def __init__(self, provider="kimi", api_key=None, model=None, api_url=None, max_tokens=None):
        self.provider = provider.lower()
        self.call_count = 0
        self.input_char_count = 0
        self.output_char_count = 0
        self.max_tokens = int(max_tokens) if max_tokens else None
        if self.provider == "kimi":
            self.api_url = api_url or "https://api.moonshot.cn/v1/chat/completions"
            self.api_key = api_key or os.getenv("KIMI_API_KEY")
            self.model = model or "kimi-k2.6"
        elif self.provider == "deepseek":
            self.api_url = api_url or "https://api.deepseek.com/chat/completions"
            self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
            self.model = model or "deepseek-chat"
        elif self.provider == "gpt":
            self.api_url = api_url or os.getenv("GPT_API_URL") or "https://sub.gratianus.net/v1/chat/completions"
            self.api_key = api_key or os.getenv("GPT_API_KEY")
            self.model = model or "gpt-5.5"
        else:
            raise ValueError(f"Unsupported provider: {provider}")
            
    def generate(self, prompt: str, system_prompt: str = "You are a database expert.", temperature: float = 0.1) -> str:
        self.call_count += 1
        self.input_char_count += len(prompt) + len(system_prompt)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }
        if self.provider == "gpt":
            # Streaming lets the proxy forward data while a long JSON response
            # is produced instead of leaving Cloudflare idle until completion.
            data["stream"] = os.getenv("GPT_STREAM", "true").strip().lower() not in {"0", "false", "no"}
            if self.max_tokens:
                data["max_completion_tokens"] = self.max_tokens
        elif self.max_tokens:
            data["max_tokens"] = self.max_tokens
        # GPT 代理模型不支持自定义 temperature（传入非默认值会返回 400），其他 provider 正常传递
        if self.provider != "gpt":
            # Current Kimi K2.6 endpoint rejects every value except 1.
            data["temperature"] = 1.0 if self.provider == "kimi" and "k2.6" in self.model.lower() else temperature
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "8"))
        base_delay = 5
        
        # 增加硬性等待机制：保证发送速率不会过快 (避免短时间内突发超过限速)
        time.sleep(0.5)
        
        for attempt in range(max_retries):
            try:
                request_timeout = int(os.getenv("GPT_REQUEST_TIMEOUT", "90")) if self.provider == "gpt" else 60
                print(f"[{self.provider.upper()}] call={self.call_count} attempt={attempt + 1}/{max_retries} "
                      f"timeout={request_timeout}s")
                response = requests.post(self.api_url, headers=headers, json=data, timeout=request_timeout)
                if response.status_code == 429:
                    if self.provider == "kimi" and os.getenv("KIMI_STRICT_KILL") == "True":
                        logger.error("Kimi Rate limited (429). KIMI_STRICT_KILL is active. Exiting process.")
                        sys.exit(137) # 使用特定的退出码表示被限频杀掉
                    wait_time = min(60, base_delay * (2 ** attempt))
                    logger.warning(f"Rate limited (429). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                response.raise_for_status()
                try:
                    output = _parse_chat_completion_response(response)
                    self.output_char_count += len(output)
                    return output
                except ValueError as e:
                    snippet = response.text[:500].replace("\n", "\\n")
                    msg = f"Invalid JSON response from {self.provider}: HTTP {response.status_code}, body={snippet!r}"
                    if attempt == max_retries - 1:
                        print(f"[{self.provider.upper()} 响应解析失败] {msg}")
                        raise LLMResponseError(msg) from e
                    wait_time = min(60, base_delay * (2 ** attempt))
                    print(f"[{self.provider.upper()} 响应解析失败] {msg}  ({wait_time}s 后重试)")
                    time.sleep(wait_time)
                    continue
            except requests.exceptions.HTTPError as e:
                # HTTP 错误：直接输出 API 返回的原始响应体
                api_err = ""
                try:
                    api_err = response.json()
                except Exception:
                    api_err = response.text
                summary = _summarize_api_error(api_err)
                if _is_non_retryable_api_error(response.status_code, api_err) or attempt == max_retries - 1:
                    print(f"[API错误] HTTP {response.status_code}: {summary}")
                    raise LLMResponseError(f"HTTP {response.status_code}: {summary}") from e
                wait_time = min(60, base_delay * (2 ** attempt))
                print(f"[API错误] HTTP {response.status_code}: {summary}  ({wait_time}s 后重试)")
                time.sleep(wait_time)
            except Exception as e:
                if isinstance(e, LLMResponseError):
                    raise
                # 网络异常（ConnectionReset 等）：输出原始异常
                if attempt == max_retries - 1:
                    print(f"[{self.provider.upper()} 连接失败] {type(e).__name__}: {e}")
                    raise LLMResponseError(str(e)) from e
                wait_time = min(60, base_delay * (2 ** attempt))
                print(f"[{self.provider.upper()} 连接失败] {type(e).__name__}: {e}  ({wait_time}s 后重试)")
                time.sleep(wait_time)
        raise LLMResponseError("Max retries exceeded")

def clean_sql(raw_sql):
    """清洗 LLM 输出，提取纯 SQL"""
    sql = raw_sql.strip()
    if '```sql' in sql:
        sql = sql.split('```sql')[1].split('```')[0].strip()
    elif '```' in sql:
        sql = sql.split('```')[1].split('```')[0].strip()
    sql = re.sub(r"<think>.*?</think>", "", sql, flags=re.IGNORECASE | re.DOTALL).strip()
    first_sql = re.search(r"\b(WITH|SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\b", sql, flags=re.IGNORECASE)
    if first_sql:
        sql = sql[first_sql.start():]
    sql = sql.replace('\n', ' ').replace('\r', ' ')
    first_token = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
    if first_token and first_token not in {"SELECT", "WITH", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"}:
        sql = "SELECT " + sql
    if not sql.endswith(';'):
        sql += ';'
    return sql

_FORBIDDEN_SQL_TOKENS = {
    "insert", "update", "delete", "merge", "create", "alter", "drop",
    "truncate", "grant", "revoke", "copy", "call", "do", "vacuum",
    "analyze", "refresh", "reindex", "cluster", "comment", "security",
}


def _sql_code_only(sql: str) -> tuple[str, list[int]]:
    """Remove literals/comments and report statement separators outside them."""
    text = str(sql)
    code = []
    separators = []
    i = 0
    while i < len(text):
        if text.startswith("--", i):
            end = text.find("\n", i + 2)
            i = len(text) if end < 0 else end + 1
            code.append(" ")
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end < 0 else end + 2
            code.append(" ")
            continue
        if text[i] == "'":
            i += 1
            while i < len(text):
                if text[i] == "'" and i + 1 < len(text) and text[i + 1] == "'":
                    i += 2
                elif text[i] == "'":
                    i += 1
                    break
                else:
                    i += 1
            code.append(" '' ")
            continue
        if text[i] == '"':
            i += 1
            while i < len(text):
                if text[i] == '"' and i + 1 < len(text) and text[i + 1] == '"':
                    i += 2
                elif text[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            code.append(' "" ')
            continue
        if text[i] == "$":
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", text[i:])
            if match:
                tag = match.group(0)
                end = text.find(tag, i + len(tag))
                i = len(text) if end < 0 else end + len(tag)
                code.append(" $$ ")
                continue
        if text[i] == ";":
            separators.append(i)
        code.append(text[i])
        i += 1
    return "".join(code), separators


def validate_readonly_sql(sql: str) -> tuple[bool, str]:
    """Conservatively allow exactly one SELECT or WITH query."""
    code, separators = _sql_code_only(sql)
    stripped = code.strip()
    if not stripped:
        return False, "Empty SQL is not executable."
    first = re.match(r"[A-Za-z]+", stripped)
    if not first or first.group(0).lower() not in {"select", "with"}:
        return False, "Only read-only SELECT or WITH queries are allowed."
    trailing = stripped.endswith(";")
    allowed_separators = 1 if trailing else 0
    if len(separators) > allowed_separators:
        return False, "Multiple SQL statements are not allowed."
    tokens = {token.lower() for token in re.findall(r"\b[A-Za-z]+\b", stripped)}
    forbidden = sorted(tokens & _FORBIDDEN_SQL_TOKENS)
    if forbidden:
        return False, f"Forbidden SQL operation: {forbidden[0].upper()}."
    return True, ""


def _safe_rollback(conn):
    """Rollback only while a psycopg2 connection is still usable."""
    if conn is None or getattr(conn, "closed", True):
        return
    try:
        conn.rollback()
    except (psycopg2.InterfaceError, psycopg2.OperationalError):
        # The original connection failure is the useful error.  A secondary
        # rollback failure must never mask it.
        pass


def _safe_close(conn):
    if conn is None or getattr(conn, "closed", True):
        return
    try:
        conn.close()
    except (psycopg2.InterfaceError, psycopg2.OperationalError):
        pass


def _is_connection_failure(exc: Exception) -> bool:
    if isinstance(exc, psycopg2.InterfaceError):
        return True
    msg = str(exc).lower()
    markers = [
        "connection to server",
        "could not connect to server",
        "connection refused",
        "operation not permitted",
        "timeout expired",
        "server closed the connection unexpectedly",
        "server terminated abnormally",
        "connection already closed",
        "ssl connection has been closed unexpectedly",
    ]
    return isinstance(exc, psycopg2.OperationalError) and any(marker in msg for marker in markers)


def execute_sql(sql, db_params):
    allowed, reason = validate_readonly_sql(sql)
    if not allowed:
        return f"ERROR: unsafe_or_forbidden_sql: {reason}"

    max_attempts = max(1, int(os.getenv("DB_CONNECTION_RETRIES", "3")))
    retry_delay = max(0.0, float(os.getenv("DB_RETRY_BASE_DELAY", "2")))
    last_connection_error = None

    for attempt in range(max_attempts):
        conn = None
        try:
            conn = psycopg2.connect(**db_params)
            conn.set_session(readonly=True, autocommit=False)
            cur = conn.cursor()
            cur.execute("SET statement_timeout = '30s';")
            cur.execute(sql)
            if cur.description:
                res = cur.fetchall()
                return json.dumps(res, ensure_ascii=False, default=str)
            return "Success"
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
            if not _is_connection_failure(exc):
                _safe_rollback(conn)
                return f"ERROR: {str(exc).strip()}"

            last_connection_error = exc
            _safe_rollback(conn)
            if attempt + 1 < max_attempts:
                wait_seconds = retry_delay * (2 ** attempt)
                logger.warning(
                    "Database connection lost; reconnecting (%s/%s) in %.1fs: %s",
                    attempt + 1,
                    max_attempts,
                    wait_seconds,
                    str(exc).strip().splitlines()[0],
                )
                time.sleep(wait_seconds)
                continue
        except Exception as exc:
            _safe_rollback(conn)
            return f"ERROR: {str(exc).strip()}"
        finally:
            _safe_close(conn)

        break

    msg = str(last_connection_error).strip() if last_connection_error else "Unknown database connection failure"
    raise DatabaseConnectionError(
        f"Database connection failed after {max_attempts} attempt(s): {msg}"
    ) from last_connection_error

