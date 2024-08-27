import multiprocessing

workers = 4  # or another reasonable number based on your server's resources
bind = "0.0.0.0:8080"
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "-"
errorlog = "-"
loglevel = "debug"