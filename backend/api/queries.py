from sqlalchemy import select

from backend.db.models import users_t


MAIN_USER_QUERY = select([
   users_t.c.id,
   users_t.c.created,
   users_t.c.email,
   users_t.c.username
]).order_by(users_t.c.id)
