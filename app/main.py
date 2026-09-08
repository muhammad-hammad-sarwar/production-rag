import os
from dotenv import load_dotenv
import logfire

load_dotenv()

logfire.configure(
    token=os.getenv("LOGFIRE_TOKEN"),
    environment="development"
)

logfire.info("Hello, Logfire! The setup was successful.")