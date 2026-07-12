FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

ENV PORT=8000
EXPOSE 8000

# Bind IPv6 (dual-stack) so the service is reachable over Fly's 6PN private
# network (fde-live-translate-ai.internal is IPv6-only). "::" also accepts IPv4,
# so local Docker / docker-compose still work.
CMD ["uvicorn", "app:app", "--host", "::", "--port", "8000"]
