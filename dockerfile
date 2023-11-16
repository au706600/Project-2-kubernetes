FROM python:3.9.12
ADD bully-algorithm.py /bully-algorithm.py
CMD [ "node", "bully-algorithm.py"]