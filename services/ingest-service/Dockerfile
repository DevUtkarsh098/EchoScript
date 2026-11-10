FROM public.ecr.aws/lambda/python:3.12
RUN dnf upgrade --releasever=2023.12.20261109 -y \
    && rm -f /usr/local/bin/aws-lambda-rie \
    && dnf clean all
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY tests ./tests
EXPOSE 8000
ENTRYPOINT ["python3.12", "-m", "uvicorn"]
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "8000"]

