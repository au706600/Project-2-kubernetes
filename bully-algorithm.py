
# BE: The algorithm in words: 

# Consider processes {Pi}^(N−1)(_i=0) and let id(Pk) = k. If Pk notices a
# non-responding coordinator, it initiates an election.
# 1. Pk sends an Election msg to all processes with higher IDs

# 2. Pk awaits OK message(s)

# - If no msg: Pk becomes leader and sends Coordinator messages to all processes with lower IDs
# If msg: Pk drops out and awaits a Coordinator message
# - If a process receives an Election message
# Respond w/ Coordinator msg if it is the process w/ highest ID
# Otherwise, respond w/ OK and take over the election

# - If a process receives a Coordinator message, it treats sender as the coordinator


# https://github.com/thecml/bully-in-kubernetes/blob/main/app.py from course
# https://www.educative.io/answers/what-is-a-bully-election-algorithm

import asyncio

import os

import socket

import random

import requests

import tornado.web

import json

import tornado.ioloop

from kubernetes import client, config


#Pod_Ip = str(os.environ['Pod_Ip'])

Pod_Ip = os.environ.get('Pod_Ip', 'localhost')

Web_Port = int(os.environ.get('Web_Port', 8000))

Pod_Id = random.randint(0, 100)

leader_pod_id = None

coordinator_pod_id = None # null

higher_id = []


#https://github.com/kubernetes-client/python
# If you need to do setup of Kubernetes, i.e. if using Kubernetes Python client
async def setup_k8s():
    #print("K8S setup completed")
    config.load_kube_config()
    v1 = client.CoreV1Api()
    print("Listing all pods with their IPs: ")
    ret = v1.list_pod_for_all_namespaces()

    for i in ret.items: 
        print(f"{i.status.pod_ip}\t{i.metadata.namespace}\t{i.metadata.name}")
    
    print("Setup completed")

async def run_bully():
    while True: 
        print("Running bully")
        # wait for everything to be set up
        await asyncio.sleep(5)

        # Get all pods doing bully

        ip_list = []
        print("Making a DNS lookup to service")
        response = socket.getaddrinfo("bully-service", 0, 0, 0, 0)
        print("Get response from DNS")

        for result in response: 
            ip_list.append(result[-1][0])
        ip_list = list(set(ip_list))

        # Remove own pod ip from the list of pods

        ip_list.remove(Pod_Ip)

        print("Got %d other pod ip's" % (len(ip_list)))

        # Get Id's of other pods by sending a GET request to them

        await asyncio.sleep(random.randint(1, 5))

        other_pods = dict()

        for pod_ip in ip_list:
            endpoint = '/pod_id' 
            url = 'http://' + str(pod_ip) + ':' + str(Web_Port) + endpoint

            response = requests.get(url)

            other_pods[str(pod_ip)] = response.json()
        
        print(other_pods)

        print(f"current leader pod id: {leader_pod_id}")

        # If P_k notices a non-responding coordinator, it initiates election by calling function
        if coordinator_pod_id == None or not check_alive(coordinator_pod_id):
            print("Initiating election")
            start_election(other_pods)
        
        else:
            # Else we do not start election due to lower id
            print("Not starting election due to lower id")

        
        # Repeat after sleeping
        await asyncio.sleep(2)

async def start_election(other_pods):
    # a list comprehension variable to get the higher id's
    higher_id = [Ip for Ip, Id in other_pods.items() if Id > Pod_Id]

    # print
    print(f"Higher id's: {higher_id}")

    # if there are, send election message to higher id's
    for Ip in higher_id:
        url = f"http://{Ip}:{Web_Port}/receive_election"
        send_data = {"sender_Pod_Id": Pod_Id}
        # Send election msg by sending a post request to the url. 
        requests.post(url, json = send_data)
        print(f"Sent election from Pod{Pod_Id} to {Ip}")
    
    # if there are no higher id's
    # start election
    if len(higher_id) == 0:
        print("No higher id's, starting election")
        leader_pod_id = Pod_Id
        print(f"The leader pod id is: {leader_pod_id}")
        send_coordinator_msg(other_pods)


    else:
        print("Starting election")
        send_election_msg(higher_id)
        print("Sent election msg")

# Function to check if if a coordinator pod is alive
async def check_alive(coordinator_pod_id):
    url = f'http://{coordinator_pod_id}:{Web_Port}/pod_id'
    try:
        # Send a get response to the URL. The return value will be a status response. 
        response = requests.get(url)
        return response.status_code == 200
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return False

# GET /pod_id
# Function to get pod id
async def pod_id(request: tornado.web.RequestHandler):
    # write the json encoded Pod_Id to the response body of the request handler. 
    request.write(json.dumps({Pod_Id}))
    # add header to the response
    request.set_header("Hello", "json")
    # finish the response
    await request.finish()

# Function to send election message 
async def send_election_msg(other_pods):
    # list comprehension variable to list for any higher id's
    higher_id = [Ip for Ip, Id in other_pods.items() if Id > Pod_Id]
    # In this for loop, we send message to higher id's. 
    for Ip in higher_id:
        #Pod_Id = Id["id"]
        #endpoint = '/receive election'
        url = f'http://{Ip}:{Web_Port}/receive_election'
        send_data = {"sender_Pod_Id": Pod_Id}
        # HTTP post request to the url with json data format. 
        try: 
            response = requests.post(url, json = send_data)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"An error occurred: {e}")
            return None
        # print
    print(f"Sent election from Pod {Pod_Id} to {Ip}")
    return response

# Function to send ok message
async def send_ok_msg(sender_pod_id):
    #endpoint = '/receive ok msg'
    # Send ok message by POST request. 
    url = f'http://{sender_pod_id}:{Web_Port}/receive_answer'
    status = {"sender_Pod_Id": 'OK'}
    try:
        response = requests.post(url, json = status)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"An error occurred: {e}")
        return None
    # print
    print(f"Sent ok message from Pod {Pod_Id} to {sender_pod_id}")
    return response


# Function to send coordinator message
async def send_coordinator_msg(other_pods):
    # list comprehension variable to list for any lower id's
    lower_id = [Ip for Ip, Id in other_pods.items() if Id < Pod_Id]
    # In this for loop, we send message to lower id's.
    for Ip in lower_id:
        #endpoint = '/receive coordinator'
        # Send coordinator message by POST request.
        url = f'http://{Ip}:{Web_Port}/receive_coordinator'
        data = {"coordinator_Pod_Id": Pod_Id}
        try:
            response = requests.post(url, json = data)
            response.raise_for_status()
        
        except requests.exceptions.HTTPError as e:
            print(f"An error occurred: {e}")
            return None
        # print
        print(f"Sent coordinator msg from Pod {Pod_Id} to {Ip}")

        return response

# POST /receive_election - election message
# The process that receives an election message sends an OK message if a node ID
# is higher than its own. It then restarts and initiates an election message. 
# The process that receives an election message sends a coordinator message if it is the node 
# with highest Id. 
async def receive_election(request: tornado.web.RequestHandler):
    # parse json
    # get sender_Pod_Id and coordinator_Pod_Id by sending GET request. 
    sender_Pod_Id = int(request.get("sender_Pod_Id"))
    coordinator_Pod_Id = int(request.get("coordinator_Pod_Id"))
    print(f"Received election message from {sender_Pod_Id}")

    # if sender_Pod_Id is higher than Pod_Id, send coordinator message
    if Pod_Id > sender_Pod_Id: 
        await send_coordinator_msg(coordinator_Pod_Id)
    # else send ok message
    else:
        await send_ok_msg(sender_Pod_Id)

# POST /receive_answer - OK message
async def receive_answer(request: tornado.web.RequestHandler):
    # parse json
    # get by sending GET request.
    status = int(request.get("sender_Pod_Id"))

    # if status is OK, print
    if status == "OK":
        print("Received OK message")
    
    # else print new coordinator
    else:
        coordinator_pod_id = request.get("coordinator_Pod_Id")
        print(f"Received coordinator message, and the new coordinator is: {coordinator_pod_id}")

# POST /receive_coordinator - Coordinator message
async def receive_coordinator(request: tornado.web.RequestHandler):
    global leader_pod_id
    # parse json
    coordinator_Pod_Id = int(request.get("coordinator_Pod_Id"))
    # print
    print(f"Received coordination message from Pod {coordinator_Pod_Id}")
    # After receiving a coordinator message, treat the sender as the coordinator
    leader_pod_id = coordinator_Pod_Id
    # send ok message to the sender
    await send_ok_msg(coordinator_Pod_Id)


async def html_handler(request: tornado.web.RequestHandler):
    with open("Kubernetes Cookies.html", "r") as file:
        content = file.read()
    request.write(content)
    await request.finish()

# Function to run bully algorithm
async def background_tasks(arg1, arg2):
    print(f"Background tasks started with {arg1} and {arg2}")
    task = asyncio.create_task(run_bully())
    yield
    task.cancel()
    await task


if __name__ == "__main__":
    # setup for kubernetes python client
    #setup_k8s()
    # Create a new tornado application with different HTTP handlers
    # by calling functions.
    app = tornado.web.Application([
        (r"/pod_id", pod_id),
        (r"/send_election_msg", send_election_msg),
        (r"/send_ok_msg", send_ok_msg),
        (r"/send_coordinator_msg", send_coordinator_msg),
        (r"/receive_election", receive_election),
        (r"/receive_answer", receive_answer),
        (r"/receive_coordinator", receive_coordinator),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "C:\\Users\\MR201\\Project-2-kubernetes"}),  # Serve static files
        (r"/", html_handler),  
    ], debug = True, autoreload = False)

    # print server starting as an indicator that the server is starting.
    print("server starting")
    # The tornado.ioloop.IOLoop.current() retrieves the I/O-loop instance.
    # Then we use the spawn_callback(background_tasks) to run the background_tasks asynchronously.
    args1 = "arg1"
    args2 = "args2"
    tornado.ioloop.IOLoop.current().spawn_callback(background_tasks, args1, args2)
    # Listen on port Web_Port, which is specified in the yml files as 8000 and the address.
    app.listen(Web_Port, address='0.0.0.0')
    # Start the I/O loop for handling requests and respond.
    tornado.ioloop.IOLoop.current().start()





