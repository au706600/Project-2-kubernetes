import requests
import asyncio

async def main():
    response = requests.get('http://python.org')

    print("Status:", response.status_code)
    print("Content-type:", response.headers['content-type'])

    html = response.text
    print("Body:", html[:15], "...")

asyncio.run(main())


#---------------

# https://github.com/thecml/bully-in-kubernetes/blob/main/app.py from course
# https://www.educative.io/answers/what-is-a-bully-election-algorithm

import asyncio

import tornado

import os

import socket

import random

import requests

import json

from tornado.web import json_response


Pod_Ip = str(os.environ('Pod_Ip'))

Web_Port = int(os.environ('Web_Port'))

Pod_Id = random.randint(0, 100)

leader_pod_id = -1

# If you need to do setup of Kubernetes, i.e. if using Kubernetes Python client
async def setup_k8s():
    print("K8S setup completed")


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

        max_pod_id = max([pod_data['Pod_Id'] for pod_data in other_pods.values()], default=-1)

        if Pod_Id > max_pod_id:
            print(f"Starting election as Pod {pod_id}")
            # delay
            await asyncio.sleep(3)
            await send_election_msg()

        else:
            print(f"Not starting election due to lower Id")


        # GET /pod_id
        async def pod_id(requests):
            pod_id_data = {"Pod_Id": Pod_Id}  
            json_response(requests, pod_id_data)

        
        async def send_election_msg():
            for pod_ip in ip_list:
                endpoint = '/receive election'
                url = 'http://' + str(pod_ip) + ':' + str(Web_Port) + endpoint
                data = {"sender_pod_id": Pod_Id}
                requests.post(url, json = data)
                print(f"Sent election from Pod {Pod_Id} to {pod_ip}")

        
        async def send_ok_msg(sender_pod_id):
            endpoint = '/receive ok msg'
            url = 'http://' + str(pod_ip) + ':' + str(Web_Port) + endpoint
            data = {"sender_pod_id": Pod_Id}
            requests.post(url, json = data)
            print(f"Sent ok message from Pod {Pod_Id} to {sender_pod_id}")


        async def send_coordinator_msg(coordinator_Pod_Id):
            for pod_ip in ip_list:
                endpoint = '/receive coordinator'
                url = 'http://' + str(pod_ip) + ':' + str(Web_Port) + endpoint
                data = {"coordinator_pod_id": coordinator_Pod_Id}
                requests.post(url, json = data)
                print(f"Sent coordinator msg from Pod {Pod_Id} to {coordinator_Pod_Id}")
            

        # POST /receive_election
        # The process that receives an election message sends an OK message if a node ID
        # is higher than its own. It then restarts and initiates an election message. 
        # The process that receives an election message sends a coordinator message if it is the node 
        # with highest Id. 
        async def receive_election(requests):
            data = await requests.json()
            sender_Pod_Id= data.get("sender_pod_id")
            coordinator_Pod_Id = data.get("coordinator_pod_id")
            print(f"Received election message from {sender_Pod_Id}")

            if pod_id > sender_Pod_Id:
                await send_ok_msg(sender_Pod_Id)
            else:
                await send_coordinator_msg(coordinator_Pod_Id)

        # POST /receive_answer
        async def receive_answer(requests):
            data = await requests.json()
            sender_Pod_Id = data.get("sender_pod_id")
            print(f"Received answer message from Pod {sender_Pod_Id}")

        # POST /receive_coordinator
        async def receive_coordinator(requests):
            data = await requests.json()
            coordinator_Pod_Id = data.get("coordinator_pod_id")
            print(f"Received coordination message from Pod {coordinator_Pod_Id}")

        async def background_tasks():
            task = asyncio.create_task(run_bully())
            yield
            task.cancel()
            await task


if __name__ == "__main__":
    asyncio.run(main())