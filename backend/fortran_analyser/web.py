"""Single-worker launcher for local use and containers."""

import asyncio
import os


def loop_factory():
    # Windows' Proactor transport can reset connections while multiprocessing
    # starts parser workers. No asyncio subprocess API is used by this service.
    return asyncio.SelectorEventLoop()


def main():
    import uvicorn

    uvicorn.run(
        "fortran_analyser.api:app",
        host=os.environ.get("FORTRAN_BIND_HOST", "127.0.0.1"),
        port=int(os.environ.get("FORTRAN_PORT", "8000")),
        loop="fortran_analyser.web:loop_factory",
    )


if __name__ == "__main__":
    main()
