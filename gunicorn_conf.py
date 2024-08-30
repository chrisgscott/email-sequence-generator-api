import multiprocessing

workers = min((multiprocessing.cpu_count() * 2) + 1, 6)  # Cap at 6 workers
bind = "0.0.0.0:8080"
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "-"
errorlog = "-"
loglevel = "debug"
timeout = 300  # 5 minutes
keepalive = 120  # How long to wait for requests on a Keep-Alive connection

# Specify the application
app = "app.main:app"