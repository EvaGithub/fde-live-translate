FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

ENV PORT=8000
EXPOSE 8000

# Bind 0.0.0.0: the app sits behind Fly's proxy (private flycast service), which
# connects to it over private IPv4. This also keeps local Docker / docker-compose
# working, where the gateway reaches it by service name on the compose network.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
