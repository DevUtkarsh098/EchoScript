from prometheus_client import Counter, Gauge, Histogram

job_submissions = Counter("echoscript_job_submissions_total", "Submitted jobs")
job_results = Counter("echoscript_job_results_total", "Completed jobs by outcome", ["status"])
active_jobs = Gauge("echoscript_active_jobs", "Active transcription jobs")
http_requests = Counter(
    "echoscript_http_requests_total",
    "HTTP requests processed by the API",
    ["method", "route", "status_code"],
)
request_duration = Histogram(
    "echoscript_http_request_duration_seconds",
    "API request latency in seconds",
    ["method", "route"],
)
