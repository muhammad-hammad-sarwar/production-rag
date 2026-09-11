# from dotenv import load_dotenv
from app.config import LOGFIRE_TOKEN
import logfire

# load_dotenv()

logfire.configure(
    token=LOGFIRE_TOKEN,
    environment="development"
)

logfire.info("Hello, Logfire! The setup was successful.")