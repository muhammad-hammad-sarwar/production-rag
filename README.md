## RUN FastAPI backend

```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## RUN Streamlit

```
PYTHONPATH=. streamlit run app/ui/streamlit_app.py
```
