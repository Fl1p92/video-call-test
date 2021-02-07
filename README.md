# video-call-test

docker exec -it backend pip-compile requirements.in --cache-dir .pip-tools
docker exec -it backend alembic revision --message="Migration message" --autogenerate
docker exec -it backend alembic upgrade head