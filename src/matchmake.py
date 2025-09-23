import logging
from .main import perform_matchmaking

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

perform_matchmaking(logger)
