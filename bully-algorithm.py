
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

leader_pod_id = -1

coordinator_pod_id = None # null

higher_id = []


#https://github.com/kubernetes-client/python
# If you need to do setup of Kubernetes, i.e. if using Kubernetes Python client
async def setup_k8s():
    #print("K8S setup completed")
    config.load_kube_config()
    v1 = client.CoreV1Api()
    print("Listing all pods with their IPs: ")
    ret = v1.list_pod_for_all_namespaces(watch = False)

    for i in ret.items: 
        print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))


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

        # If P_k notices a non-responding coordinator, it initiates election. 
       # max_pod_id = max([pod_data['Pod_Id'] for pod_data in other_pods.values()], default=-1)

        if coordinator_pod_id == None or not check_alive():
            print("Initiating election")
            start_election()
        
        else:
            print("Not starting election due to lower id")
        
        # Repeat after sleeping
        await asyncio.sleep(2)

async def start_election():
    pass

async def check_alive():
    endpoint = '/pod_id'
    url = 'http://' + str(Pod_Id) + str(Web_Port) + endpoint
    try:
        response = requests.get(url)
        return response.status_code == 200
    
    except requests.exceptions.RequestException as e:
        print("An error occurred: {e}")

# GET /pod_id
async def pod_id(request: tornado.web.RequestHandler):
    request.write(json.dumps({Pod_Id}))
    request.set_header("Hello", "json")
    await request.finish()

# Function to send election message
async def send_election_msg(ip_list):
    # list comprehension
    higher_id = [Id for Id in ip_list if Id['id'] > Pod_Id]
    for Id in higher_id:
        Pod_Id = Id["id"]
        endpoint = '/receive election'
        url = 'http://' + str(Pod_Id) + ':' + str(Web_Port) + endpoint
        send_data = {"sender_Pod_Id": Pod_Id}
        requests.post(url, json = send_data)
        print(f"Sent election from Pod {Pod_Id} to {Pod_Ip}")
    

# Function to send ok message
async def send_ok_msg(sender_pod_id):
    endpoint = '/receive ok msg'
    url = 'http://' + str(Pod_Ip) + ':' + str(Web_Port) + endpoint
    status = {"sender_Pod_Id": 'OK'}
    send = requests.post(url, json = status)
    print(f"Sent ok message from Pod {Pod_Id} to {sender_pod_id}")
    return send


# Function to send coordinator message
async def send_coordinator_msg(coordinator_Pod_Id, ip_list):
    # list comprehension
    lower_id = [Id for Id in ip_list if Id['id'] < Pod_Id]
    for pod_ip in ip_list:
        endpoint = '/receive coordinator'
        url = 'http://' + str(pod_ip) + ':' + str(Web_Port) + endpoint
        data = {"coordinator_Pod_Id": coordinator_Pod_Id}
        requests.post(url, json = data)
        print(f"Sent coordinator msg from Pod {Pod_Id} to {coordinator_Pod_Id}")

        # For lower processes, send the coordinator msg
    if Pod_Id < lower_id:
        endpoint = '/receive coordinator msg'
        url = 'http://' + str(Pod_Ip) + ':' + str(Web_Port) + endpoint
        data = {"coordinator_Pod_Id": coordinator_Pod_Id}
        send = requests.post(url, json = data)
        print(f"Sent election from Pod {Pod_Id} to {Pod_Ip}")
    
    return send
    

# POST /receive_election - election message
# The process that receives an election message sends an OK message if a node ID
# is higher than its own. It then restarts and initiates an election message. 
# The process that receives an election message sends a coordinator message if it is the node 
# with highest Id. 
async def receive_election(request: tornado.web.RequestHandler):
    # parse json
    sender_Pod_Id = await int(request.get("sender_Pod_Id"))
    coordinator_Pod_Id = await int(request.get("coordinator_Pod_Id"))
    print(f"Received election message from {sender_Pod_Id}")

    if Pod_Id > sender_Pod_Id: 
        await send_coordinator_msg(coordinator_Pod_Id)
    else:
        await send_ok_msg(sender_Pod_Id)

# POST /receive_answer - OK message
async def receive_answer(request: tornado.web.RequestHandler):
    status = request.get("sender_Pod_Id")

    if status == "OK":
        print("Received OK message")
    
    else:
        coordinator_pod_id = request.get("coordinator_Pod_Id")
        print(f"Received coordinator message, and the new coordinator is: {coordinator_pod_id}")

# POST /receive_coordinator - Coordinator message
async def receive_coordinator(request: tornado.web.RequestHandler):
    global leader_pod_id
    coordinator_Pod_Id = await int(request.get("coordinator_Pod_Id"))
    print(f"Received coordination message from Pod {coordinator_Pod_Id}")
    # After receiving a coordinator message, treat the sender as the coordinator
    leader_pod_id = coordinator_Pod_Id


async def background_tasks():
    task = asyncio.create_task(run_bully())
    yield
    task.cancel()
    await task


if __name__ == "__main__":
    app = tornado.web.Application()
    app.add_handlers('.*',[  
        ('/pod_id', pod_id),
        ('/send_election_msg', send_election_msg),
        ('/send_ok', send_ok_msg),
        ('/send_coordinator_msg', send_coordinator_msg),
        ('/receive_election', receive_election),
        ('/receive_answer', receive_answer),
        ('/receive_coordinator', receive_coordinator)
    ])
    print("server starting")
    tornado.ioloop.IOLoop.spawn_callback(background_tasks)
    app.listen(Web_Port, address='0.0.0.0')
    tornado.ioloop.IOLoop.current().start()

