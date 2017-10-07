FROM python:3.6

ADD turg /app
ADD config.yml /config.yml
ADD requirements.txt /requirements.txt
RUN pip install -r requirements.txt
RUN pip install gunicorn

WORKDIR /app
ENV PYTHONPATH /

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/gunicorn", "turg.main:app"]
CMD ["-b", "0.0.0.0:8080", "-t", "60", "--worker-class", "aiohttp.worker.GunicornUVLoopWebWorker"]
