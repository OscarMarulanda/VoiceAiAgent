"""CLI tool for testing the agent without voice or chat.

Usage:
    python -m app.agent.test_cli              # chat mode (default)
    python -m app.agent.test_cli --channel voice   # voice mode (short responses)
"""

import argparse
import asyncio
import sys

from app.database import init_pool, close_pool
from app.agent.core import process_message
from app.repositories import session_repo


async def main(channel: str) -> None:
    await init_pool()

    session = await session_repo.create_session(channel=channel)
    session_id = session["id"]
    print(f"Session: {session_id}  |  Channel: {channel}")
    print("Type 'quit' or 'exit' to end. Ctrl+C also works.\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break
            if not user_input or user_input.lower() in ("quit", "exit"):
                break
            response = await process_message(session_id, user_input)
            print(f"Agent: {response}\n")
    except KeyboardInterrupt:
        print()
    finally:
        try:
            await session_repo.end_session(session_id)
            await close_pool()
        except BaseException:
            pass
        print("Session ended.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the agent via CLI")
    parser.add_argument(
        "--channel",
        choices=["chat", "voice"],
        default="chat",
        help="Channel mode: chat (longer responses) or voice (short responses)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.channel))
