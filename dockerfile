FROM python:3.12.1

#ADD bully-algorithm.py /bully-algorithm.py

WORKDIR /app

# Copy all to current dir
COPY . /app

# Copy requirements to container and install
#COPY requirements.txt requirements.txt
#COPY FortuneCookies.txt FortuneCookies.txt

RUN pip install -r requirements.txt

EXPOSE 8000
# This will print python logs to output
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

CMD [ "python", "-u", "bully-algorithm.py"]