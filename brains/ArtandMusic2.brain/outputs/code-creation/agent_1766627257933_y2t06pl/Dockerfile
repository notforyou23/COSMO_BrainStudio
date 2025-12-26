# syntax=docker/dockerfile:1
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup -S app && adduser -S -G app app \
    && mkdir -p /out /outputs \
    && chown -R app:app /app /out /outputs

COPY scripts/ /app/scripts/

USER app

ENTRYPOINT ["python","-u"]
CMD ["scripts/smoke_test.py"]
