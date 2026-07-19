.PHONY: up down down-volumes logs build restart shell test seed

up:
	docker compose up -d

down:
	docker compose down

down-volumes:
	docker compose down -v

logs:
	docker compose logs -f app

build:
	docker compose build

restart:
	docker compose restart

shell:
	docker compose exec app bash

test:
	docker compose exec app pytest

seed:
	docker compose exec app python scripts/seed_data.py
