FROM python:3.8-slim-buster

WORKDIR /app

RUN apt-get update && apt-get install -y portaudio19-dev python3-pyaudio gcc

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 5000 50051

# run the command
CMD ["python3", "./mafia_server.py"]
