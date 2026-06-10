from pathlib import Path
import dotenv

dotenv.load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from database import init_db

try:
    init_db()
    print('init_db succeeded')
except Exception as e:
    import traceback

    print('init_db failed:')
    traceback.print_exc()

