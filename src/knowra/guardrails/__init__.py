import os
from dotenv import load_dotenv
from nemoguardrails import LLMRails, RailsConfig

load_dotenv()

if "NVIDIA_API_KEY" in os.environ and "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["NVIDIA_API_KEY"]

_rails = None


def get_rails() -> LLMRails:
    global _rails
    if _rails is None:
        config = RailsConfig.from_path(os.path.dirname(__file__))
        _rails = LLMRails(config)
    return _rails
