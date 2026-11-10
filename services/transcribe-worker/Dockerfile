FROM public.ecr.aws/lambda/python:3.12
RUN dnf upgrade --releasever=2023.12.20261109 -y \
    && rm -f /usr/local/bin/aws-lambda-rie \
    && dnf clean all
WORKDIR /worker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker ./worker
ENTRYPOINT ["python3.12", "-m", "worker.main"]

