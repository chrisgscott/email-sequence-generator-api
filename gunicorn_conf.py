import multiprocessing

workers = 8
bind = "0.0.0.0:8080"
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "-"
errorlog = "-"
loglevel = "debug"