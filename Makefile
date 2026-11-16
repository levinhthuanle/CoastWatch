.PHONY: up down build logs shell-backend shell-db migrate seed

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f

shell-backend:
	docker-compose exec backend bash

shell-db:
	docker-compose exec db psql -U coastwatch -d coastwatch

migrate:
	docker-compose exec backend alembic upgrade head

seed:
	docker-compose exec backend python scripts/seed_data.py

restart-backend:
	docker-compose restart backend

restart-frontend:
	docker-compose restart frontend
