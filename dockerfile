FROM python:3.12.1


WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements to container and install
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
 
# Upgrade pip
RUN pip install --upgrade pip

# Copy all to current dir
COPY . .

# Make port 8000 available for api
EXPOSE 8000

# This will print python logs to output
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# Define the command to be run when launching the container
CMD ["python", "-u", "./bully-algorithm.py"]

