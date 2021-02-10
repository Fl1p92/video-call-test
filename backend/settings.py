import os
from decimal import Decimal


ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', [])

BACKEND_PORT = int(os.environ.get('BACKEND_PORT', 8080))

DB_URL = os.environ.get('DB_URL', 'driver://user:pass@localhost/dbname')

DB_INFO = DB_URL.split(':')[0]

# Default bill balance for new users, 0$
DEFAULT_BALANCE = Decimal('0.00')

# Default tariff, 50 cent
DEFAULT_TARIFF = Decimal('0.50')
