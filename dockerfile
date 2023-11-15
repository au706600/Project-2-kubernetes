FROM node:7
ADD bully-algorithm.py /bully-algorithm.py
CMD [ "node", "bully-algorithm.py"]