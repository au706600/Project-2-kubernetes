
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



#--------------------------------------------------------------------------------

import asyncio
import os
import socket
import random
import json
import time
from tornado.httpclient import AsyncHTTPClient
import tornado.web
import tornado.ioloop
from kubernetes import config

def get_podId(): 
    name = os.environ.get("Pod_Id", "")
    return int(name.split("-")[-1])

Pod_Ip = os.environ.get('Pod_Ip', socket.gethostbyname(socket.gethostname()))
Web_Port = int(os.environ.get('Web_Port', 8000))
#Pod_Id = int(os.environ.get('Pod_Id', random.randint(1, 1000)))
Pod_Id = get_podId()
Service_DNS = os.environ.get('SERVICE_DNS', 'bully-service')

leader_pod_id = None
coordinator_pod_ip = None
coordinator_received = False
received_ok = False
other_pods = {}
start_time = time.time()
http_client = AsyncHTTPClient()

# -----------------------------
# Tornado Handlers
class PodIdHandler(tornado.web.RequestHandler):
    async def get(self):
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({"Pod_Id": Pod_Id, "Pod_Ip": Pod_Ip}))
        self.finish()

class ElectionHandler(tornado.web.RequestHandler):
    async def post(self):
        data = json.loads(self.request.body.decode('utf-8'))
        sender_pod_id = int(data.get("sender_Pod_Id"))
        sender_pod_ip = data.get("sender_Pod_Ip")
        print(f"Received election from {sender_pod_id} ({sender_pod_ip})")
        await receive_election(sender_pod_id, sender_pod_ip)
        self.write({"status": "ACK"})

class AnswerHandler(tornado.web.RequestHandler):
    async def post(self):
        data = json.loads(self.request.body.decode('utf-8'))
        sender_pod_id = data.get("sender_Pod_Id")
        sender_pod_ip = data.get("sender_Pod_Ip")
        status = data.get("status")
        coordinator_id = data.get("coordinator_Pod_Id")
        coordinator_ip = data.get("coordinator_Pod_Ip")
        await receive_answer(sender_pod_id, sender_pod_ip, status, coordinator_id, coordinator_ip)
        self.write({"status": "ACK"})

class CoordinatorHandler(tornado.web.RequestHandler):
    async def post(self):
        data = json.loads(self.request.body.decode('utf-8'))
        coordinator_id = int(data.get("coordinator_Pod_Id"))
        coordinator_ip = data.get("coordinator_Pod_Ip")
        print(f"Received coordinator message from {coordinator_id} ({coordinator_ip})")
        await receive_coordinator(coordinator_id, coordinator_ip)
        self.write({"status": "ACK"})

class healthHandler(tornado.web.RequestHandler):
    async def get(self):
        uptime = time.time() - start_time
        # Always return 200 so probes pass once server is up
        self.set_status(200)
        self.write({
            "status": "OK",
            "uptime_seconds": uptime,
            "pod_id": Pod_Id,
            "leader": leader_pod_id or "unknown"
        })
        self.finish()

class htmlHandler(tornado.web.RequestHandler):
    async def get(self):
        try:
            with open("index.html", "r") as file:
                content = file.read()
            self.write(content)
            self.set_header("Content-Type", "text/html")
        except FileNotFoundError:
            self.set_status(404)
            self.write("HTML file not found.")
            self.finish()

# -----------------------------
# Kubernetes Setup
async def setup_k8s():
    try:
        try:
            config.load_incluster_config()
            print("Loaded in-cluster Kubernetes configuration")
        except:
            config.load_kube_config()
            print("Loaded local kubeconfig")
        print("Kubernetes config loaded")
    except Exception as e:
        print(f"Kubernetes setup failed: {str(e)}")
        print("Continuing without cluster API")

# -----------------------------
# Pod Discovery via DNS
async def discover_pods():
    try:
        _, _, pod_ips = socket.gethostbyname_ex(Service_DNS)
        return [ip for ip in pod_ips if ip != Pod_Ip]
    except Exception as e:
        print(f"[Pod {Pod_Id}] DNS discovery failed: {e}")
        return []

# -----------------------------

# Bully Algorithm
async def run_bully():
    global Pod_Ip, leader_pod_id, coordinator_pod_ip, coordinator_received, Pod_Id, other_pods

    print(f"[Pod {Pod_Id}] Waiting 20s before starting elections...")
    await asyncio.sleep(20)  # Let the cluster stabilize

    while True:
        print(f"[Pod {Pod_Id}] Running bully algorithm iteration")
        await asyncio.sleep(15)

        try:
            pod_ips = await discover_pods()
            if not pod_ips:
                print(f"[Pod {Pod_Id}] No other pods found, skipping election")
                await asyncio.sleep(5)
                continue

            # Collect pod IDs
            other_pods = {}
            for pod_ip in pod_ips:
                try:
                    url = f"http://{pod_ip}:{Web_Port}/pod_id"
                    response = await http_client.fetch(url, request_timeout=2.0)
                    body = json.loads(response.body.decode('utf-8')) or {}
                    peer_id = int(body.get("Pod_Id", 0))
                    peer_ip = body.get("Pod_Ip", pod_ip)
                    if peer_id > 0:
                        other_pods[peer_ip] = peer_id
                except Exception as e:
                    print(f"[Pod {Pod_Id}] Error contacting pod {pod_ip}: {str(e)}")
                    continue

            print(f"[Pod {Pod_Id}] Other pods: {other_pods}")

            # Check leader
            coordinator_alive = False
            if coordinator_pod_ip:
                coordinator_alive = await check_alive(coordinator_pod_ip)
                print(f"[Pod {Pod_Id}] Coordinator status: {'alive' if coordinator_alive else 'not responding'}")

            if not coordinator_pod_ip or not coordinator_alive:
                print(f"[Pod {Pod_Id}] Starting election process")
                coordinator_received = False
                await start_election(other_pods)

                for _ in range(5):
                    if coordinator_received:
                        print(f"[Pod {Pod_Id}] New coordinator established: {leader_pod_id}")
                        break
                    await asyncio.sleep(5)

                if not coordinator_received:
                    print(f"[Pod {Pod_Id}] Assuming leadership (no coordinator received)")
                    leader_pod_id = Pod_Id
                    coordinator_pod_ip = Pod_Ip
                    await send_coordinator_msg(other_pods)
            else:
                print(f"[Pod {Pod_Id}] Coordinator {leader_pod_id} is healthy")

        except Exception as e:
            print(f"[Pod {Pod_Id}] Critical error in bully algorithm: {str(e)}")
            await asyncio.sleep(5)

        await asyncio.sleep(2)

async def start_election(peers_map):
    global Pod_Id, leader_pod_id, coordinator_pod_ip, received_ok, coordinator_received
    print(f"[Pod {Pod_Id}] Starting election... peers: {peers_map}")

    higher_id = {ip: pid for ip, pid in peers_map.items() if pid > Pod_Id}
    print(f"[Pod {Pod_Id}] Higher-id peers: {higher_id}")

    if not higher_id:
        print(f"[Pod {Pod_Id}] No higher ID peers found. Declaring self as leader.")
        leader_pod_id = Pod_Id
        coordinator_pod_ip = Pod_Ip
        await send_coordinator_msg(peers_map)
        return

    received_ok = False
    for ip, pid in higher_id.items():
        if not await check_alive(ip):
            print(f"[Pod {Pod_Id}] Skipping Pod {ip} (id = {pid}) - not alive")
            continue
        try:
            url = f'http://{ip}:{Web_Port}/receive_election'
            payload = {"sender_Pod_Id": Pod_Id, "sender_Pod_Ip": Pod_Ip}
            await http_client.fetch(url, method='POST', body=json.dumps(payload), request_timeout=3.0)
            print(f"[Pod {Pod_Id}] Sent ELECTION to Pod {pid} ({ip})")
        except Exception as e:
            print(f"[Pod {Pod_Id}] Failed to send election to Pod {pid}: {e}")
        
    await asyncio.sleep(5)
    if not received_ok:
        print(f"[Pod {Pod_Id}] No OK responses. Declaring self as leader.")
        leader_pod_id = Pod_Id
        coordinator_pod_ip = Pod_Ip
        coordinator_received = True
        await send_coordinator_msg(peers_map)

# -----------------------------
# Communication Helpers
async def check_alive(pod_ip):
    if not pod_ip:
        return False
    try:
        url = f'http://{pod_ip}:{Web_Port}/health'
        response = await http_client.fetch(url, request_timeout=2.0)
        return response.code == 200
    except Exception:
        return False

async def send_ok_msg(receiver_pod_ip):
    if not receiver_pod_ip:
        return False
    try:
        url = f'http://{receiver_pod_ip}:{Web_Port}/receive_answer'
        payload = {"sender_Pod_Id": Pod_Id, "sender_Pod_Ip": Pod_Ip, "status": "OK"}
        await http_client.fetch(url, method='POST', body=json.dumps(payload), request_timeout=3.0)
        print(f"Sent OK from Pod {Pod_Id} to {receiver_pod_ip}")
        return True
    except Exception as e:
        print(f"Error sending OK: {e}")
        return False

async def send_coordinator_msg(peers_map):
    global Pod_Id, coordinator_pod_ip
    lower_id = {ip: pid for ip, pid in peers_map.items() if pid < Pod_Id}
    print(f"[Pod {Pod_Id}] Sending coordinator message to lower IDs: {lower_id}")
    for ip, pid in lower_id.items():
        try:
            url = f'http://{ip}:{Web_Port}/receive_coordinator'
            data = {"coordinator_Pod_Id": Pod_Id, "coordinator_Pod_Ip": Pod_Ip}
            await http_client.fetch(url, method='POST', body=json.dumps(data), request_timeout=2.0)
            print(f"[Pod {Pod_Id}] Sent COORDINATOR to {ip} (id={pid})")
        except Exception as e:
            print(f"[WARN] Failed to send COORDINATOR to {ip}: {e}")

# -----------------------------
# Message Receivers
async def receive_election(sender_pod_id, sender_pod_ip):
    global Pod_Id, other_pods
    print(f"[Pod {Pod_Id}] receive_election from {sender_pod_id} ({sender_pod_ip})")
    if sender_pod_ip:
        other_pods[sender_pod_ip] = int(sender_pod_id)
    if Pod_Id > int(sender_pod_id):
        await send_ok_msg(sender_pod_ip)
        await start_election(other_pods)
    else:
        print(f"Pod {Pod_Id} received election from higher pod, no OK sent")

async def receive_answer(sender_id, sender_ip, status, coordinator_id, coordinator_ip):
    global coordinator_pod_ip, leader_pod_id, coordinator_received, received_ok
    print(f"[Pod {Pod_Id}] receive_answer: status={status}, from {sender_id} ({sender_ip})")
    try:
        if sender_ip and sender_id is not None:
            other_pods[sender_ip] = int(sender_id)
    except Exception:
        pass
    if status == "OK":
        print(f"[Pod {Pod_Id}] Received OK from {sender_ip}")
        received_ok = True
        return
    if coordinator_id and coordinator_ip:
        try:
            leader_pod_id = int(coordinator_id)
            coordinator_pod_ip = coordinator_ip
            coordinator_received = True
            print(f"[Pod {Pod_Id}] Adopted coordinator: {leader_pod_id} ({coordinator_pod_ip})")
        except Exception as e:
            print(f"[ERROR] Failed to process coordinator message: {e}")

async def receive_coordinator(coordinator_id, coordinator_ip):
    global leader_pod_id, coordinator_received, coordinator_pod_ip
    print(f"[Pod {Pod_Id}] receive_coordinator: leader {coordinator_id} ({coordinator_ip})")
    try:
        leader_pod_id = int(coordinator_id)
        coordinator_pod_ip = coordinator_ip
        coordinator_received = True
        await send_ok_msg(coordinator_ip)
    except Exception as e:
        print(f"[ERROR] Failed to process coordinator message: {e}")

# -----------------------------
# Background Runner
async def background_tasks():
    try:
        print("Background tasks started")
        task = asyncio.create_task(run_bully())
        await task
    except asyncio.CancelledError:
        print("Background tasks cancelled")

# -----------------------------
if __name__ == "__main__":
    async def main():
        await setup_k8s()
        try:
            app = tornado.web.Application([
                (r"/pod_id", PodIdHandler),
                (r"/receive_election", ElectionHandler),
                (r"/receive_answer", AnswerHandler),
                (r"/receive_coordinator", CoordinatorHandler),
                (r"/health", healthHandler),
                (r"/(.*\.css)", tornado.web.StaticFileHandler, {"path": "/app"}),
                (r"/", htmlHandler),
            ], debug=True, autoreload=False)

            app.listen(Web_Port, address='0.0.0.0')
            print(f"Server started on http://{Pod_Ip}:{Web_Port}")

            loop = asyncio.get_event_loop()
            loop.create_task(background_tasks())
            #tornado.ioloop.IOLoop.current().start()
            await asyncio.Event().wait()

        except Exception as e:
            print(f"Startup error: {str(e)}")
            raise

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Critical failure: {str(e)}")
        import traceback
        traceback.print_exc()







