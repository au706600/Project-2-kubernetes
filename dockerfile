FROM python:3.9.12
ADD bully-algorithm.py /bully-algorithm.py
COPY requests requests
RUN pip install requests
EXPOSE 8000
# This will print python logs to output
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8
CMD [ "python", "bully-algorithm.py"]