FROM python:3.12-slim

WORKDIR /app

# libs/message_broker is installed as an editable path dependency, so the
# build context must be the repo root (see docker-compose.yml) and both
# paths need to exist before `pip install -r requirements.txt` resolves it.
COPY libs/message_broker /libs/message_broker
COPY services/playstore-scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/playstore-scraper/scraper ./scraper

CMD ["python", "-m", "scraper.main"]
