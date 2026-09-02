up:
	docker compose up --build

down:
	docker compose down

reset:
	docker compose down -v

logs:
	docker compose logs -f backend

api:
	python -m uvicorn backend.app.main:app --reload
