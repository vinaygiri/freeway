"""Freeway-as-a-library quickstart.

Run:  uv run python examples/library_quickstart.py
Reads keys from your environment / ~/.freeway/.env (or pass them explicitly).
"""

from __future__ import annotations

import asyncio
import os

from freeway import Freeway


def sync_example() -> None:
    fw = Freeway(
        primary="gemini/models/gemini-2.5-flash",
        fallbacks=["cerebras/gpt-oss-120b"],
        keys={
            "gemini": os.environ.get("GEMINI_API_KEY", ""),
            "cerebras": os.environ.get("CEREBRAS_API_KEY", ""),
        },
    )
    completion = fw.chat(
        messages=[{"role": "user", "content": "Reply with the single word OK."}],
        max_tokens=32,
    )
    print("text        :", completion.text.strip())
    print("served_model:", completion.served_model)
    print("was_fallback:", completion.was_fallback)
    print("stop_reason :", completion.stop_reason)
    print("in/out tok  :", completion.input_tokens, "/", completion.output_tokens)


async def stream_example() -> None:
    fw = Freeway.from_env()
    print("\nstreaming:")
    async for event in fw.astream(
        messages=[{"role": "user", "content": "Count to five."}],
        max_tokens=64,
    ):
        if event.type == "text":
            print(event.text, end="", flush=True)
        elif event.type == "done" and event.completion:
            print(f"\n(served by {event.completion.served_model})")


if __name__ == "__main__":
    sync_example()
    asyncio.run(stream_example())
