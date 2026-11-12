FROM public.ecr.aws/lambda/python:3.12 AS runtime
RUN dnf upgrade --releasever=2023.12.20261109 -y \
    && rm -f /usr/local/bin/aws-lambda-rie \
    && dnf clean all
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

FROM public.ecr.aws/lambda/python:3.12 AS ci-test
RUN dnf upgrade --releasever=2023.12.20261109 -y && dnf clean all
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest==8.3.4
COPY app ./app
COPY tests ./tests
RUN python3.12 -m pytest -q tests

FROM runtime
EXPOSE 8000
ENTRYPOINT ["python3.12", "-m", "uvicorn"]
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "8000"]
