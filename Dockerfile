FROM python:3.11-alpine as build
ENV PYTHONPATH=.\
    DOCKER=true

RUN apk add --no-cache -u gcc make musl-dev tini

RUN pip install pdm
WORKDIR /app/
RUN mkdir __pypackages__
COPY pyproject.toml pdm.lock /app/

RUN pdm sync --prod --no-editable

FROM python:3.11-alpine as prod
ENV PYTHONPATH=".:/pkgs"\
    DOCKER=true

WORKDIR /app/

RUN apk add --no-cache tini

COPY --from=build /app/__pypackages__/3.11/lib /pkgs
COPY . .
ENTRYPOINT ["tini", "--"]

CMD ["python3", "-u", "/app/run.py"]
