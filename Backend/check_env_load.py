from pathlib import Path
import os
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
    print('loaded dotenv')
except Exception as e:
    print('dotenv import/load failed:', e)
    print('DATABASE_URL set=', bool(os.getenv('DATABASE_URL')))
    print('PG_HOST=', os.getenv('PG_HOST'))
    print('PG_PORT=', os.getenv('PG_PORT'))
    print('PG_USER=', os.getenv('PG_USER'))
    print('PG_DATABASE=', os.getenv('PG_DATABASE'))
