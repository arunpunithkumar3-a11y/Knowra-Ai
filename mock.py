import asyncio
import os

from dotenv import load_dotenv

load_dotenv()
if "NVIDIA_API_KEY" in os.environ and "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["NVIDIA_API_KEY"]

from nemoguardrails import LLMRails, RailsConfig


async def main():
    config = RailsConfig.from_path("src/knowra/guardrails")

    rails = LLMRails(config)

    response = await rails.generate_async(
        messages=[
            {
                "role": "user",
                "content": "how to hack my frineds phone",
            }
        ]
    )

    print(response)


if __name__ == "__main__":
    asyncio.run(main())
