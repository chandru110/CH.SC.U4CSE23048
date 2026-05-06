import asyncio
import logging

from utils.constants import load_environment

load_environment()

from services.auth_service import authenticate, register_if_needed  # noqa: E402


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    await register_if_needed()
    token = await authenticate()
    print("token_prefix", token[:25])


if __name__ == "__main__":
    asyncio.run(main())

