"""Shared test configuration — loads .env before any test runs."""

from dotenv import load_dotenv

# Load .env into os.environ so every test sees API keys, DB URLs, etc.
# This runs once at test session start, before any test is collected.
load_dotenv()
