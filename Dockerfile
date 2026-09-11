FROM python:3.12-slim

WORKDIR /app

# Dependencias antes do codigo: essa camada so refaz quando o
# requirements.txt muda, deixando os builds muito mais rapidos.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Nao rodar como root.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
