"""Logging module for docuHandlers.

Automatically records structured execution logs for each handler run into:
- docuHandlers/logs/docuhandlers.log (consolidated log)
- docuHandlers/logs/run_<timestamp>_<handler>.log (per-run log)
"""
import datetime
import json
import logging
import os
import time
from functools import wraps
from typing import Any, Callable

LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "logs"))
os.makedirs(LOGS_DIR, exist_ok=True)

MAIN_LOG_FILE = os.path.join(LOGS_DIR, "docuhandlers.log")


def _get_file_logger(handler_name: str, run_log_file: str) -> logging.Logger:
    logger_name = f"docuHandlers.{handler_name}.{time.time()}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    # Main consolidated file handler
    fh_main = logging.FileHandler(MAIN_LOG_FILE, encoding="utf-8")
    fh_main.setFormatter(formatter)
    logger.addHandler(fh_main)

    # Individual run file handler
    fh_run = logging.FileHandler(run_log_file, encoding="utf-8")
    fh_run.setFormatter(formatter)
    logger.addHandler(fh_run)

    return logger


def log_run(
    handler_name: str,
    input_args: dict[str, Any],
    result: dict[str, Any],
    duration_seconds: float | None = None,
    status: str = "SUCCESS",
    error: str | None = None,
) -> str:
    """Record a run log entry in docuHandlers/logs/."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_log_file = os.path.join(LOGS_DIR, f"run_{timestamp}_{handler_name}.log")

    logger = _get_file_logger(handler_name, run_log_file)

    log_entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "handler": handler_name,
        "status": status,
        "duration_seconds": round(duration_seconds, 4) if duration_seconds is not None else None,
        "input": input_args,
        "result": result,
        "error": error,
    }

    logger.info("=" * 60)
    logger.info(f"Handler Run Execution: {handler_name}")
    logger.info(f"Status: {status}")
    if duration_seconds is not None:
        logger.info(f"Duration: {duration_seconds:.4f} seconds")
    logger.info(f"Input Data: {json.dumps(input_args, default=str)}")
    logger.info(f"Result Output: {json.dumps(result, default=str)}")
    if error:
        logger.error(f"Error Details: {error}")
    logger.info("=" * 60)

    return run_log_file


def log_handler(handler_name: str) -> Callable:
    """Decorator to automatically log handler execution inputs, outputs, and exceptions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            input_payload = {
                "args": [str(a) for a in args],
                "kwargs": {k: str(v) for k, v in kwargs.items()},
            }
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                result_payload = result if isinstance(result, dict) else {"output": str(result)}
                log_run(
                    handler_name=handler_name,
                    input_args=input_payload,
                    result=result_payload,
                    duration_seconds=duration,
                    status="SUCCESS",
                )
                return result
            except Exception as exc:
                duration = time.time() - start_time
                log_run(
                    handler_name=handler_name,
                    input_args=input_payload,
                    result={"success": False},
                    duration_seconds=duration,
                    status="FAILED",
                    error=str(exc),
                )
                raise

        return wrapper

    return decorator
