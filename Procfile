web: uvicorn app.main:app --host=0.0.0.0 --port=$PORT
release: python -c "import sys; sys.path.append('.'); from sr_screener.database import init_db; init_db()"
