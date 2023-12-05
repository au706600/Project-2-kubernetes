FROM python:3.9.12
ADD bully-algorithm.py /bully-algorithm.py
# Copy requirements to container and install
COPY requirements.txt requirements.txt
COPY FortuneCookies.txt FortuneCookies.txt
RUN pip install -r requirements.txt
# Copy all to current dir
COPY . .

EXPOSE 8000
# This will print python logs to output
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

CMD [ "python", "bully-algorithm.py"]