from pathlib import Path
import sys

# Ensure project root is on import path when running directly
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.database.models import Base
from core.database.session import get_engine


def main() -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Banco SQLite inicializado em ./data/emails.db")


if __name__ == "__main__":
    main()