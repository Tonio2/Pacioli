dev:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload &
	cd frontend && npm run dev
