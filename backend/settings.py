import os
from datetime import timedelta
from decimal import Decimal


ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', [])

BACKEND_PORT = int(os.environ.get('BACKEND_PORT', 8080))

DB_URL = os.environ.get('DB_URL', 'driver://user:pass@localhost/dbname')

DB_INFO = DB_URL.split(':')[0]

# Default bill balance for new users, 0$
DEFAULT_BALANCE = Decimal('0.00')

# Default tariff, 50 cent
DEFAULT_TARIFF = Decimal('0.50')

# JWT secret
JWT_SECRET = os.environ.get('JWT_SECRET', 'top_secret')
JWT_EXPIRATION_DELTA = timedelta(days=int(os.environ.get('JWT_EXPIRATION_DELTA_DAYS', 14)))
