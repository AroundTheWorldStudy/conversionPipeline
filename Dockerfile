# start from a slim Python image
FROM python:3.11

# install ffmpeg via apt
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# set working dir
WORKDIR /app

# copy & install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app code
COPY run.py .

# tell Flask where the app is
ENV FLASK_APP=app.py

# expose port and run
EXPOSE 8080
CMD ["python3", "run.py"]
