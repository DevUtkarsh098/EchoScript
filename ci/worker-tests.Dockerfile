ARG WORKER_IMAGE
FROM ${WORKER_IMAGE}
RUN pip install --no-cache-dir pytest==8.3.4
COPY tests ./tests
ENTRYPOINT ["python3.12", "-m", "pytest"]
CMD ["-q", "tests"]
