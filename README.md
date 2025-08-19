# Kubernetes Fortune Cookie with Bully Algorithm

A kubernetes-based web application that serves fortune cookies and has the goal of ensuring high availability with a leader election using the Bully algorithm. 
The elected leader pod is responsible for serving the website. If the leader fails, a leader is elected via the Bully algorithm. 

## 📚 Table of Contents

- [📘 Project Description](#-project-description)
- [🧰 Prerequisites](#-prerequisites)
- [✨ Features](#-features)
- [🛠️ Tech Stack](#tech-stack)
- [📦 Installation & Deployment](#-installation)
- [🧱 Directory Structure](#-directory-structure-of-ai-resume-analyzer)
- [🎥 Demo](#-demo)
- [⚠️ Issues/Problems](#-issues/problems)

## 📘 Project Description

This project implements a distributed web service hosted on Kubernetes where users can click a button to receive a random fortune cookie.
The system demonstrates:

- A Kubernetes Deployment with multiple pods.

- A Bully Algorithm implementation for leader election.

- A leader pod serving the website (HTML/CSS/JavaScript).

- A new leader, when the current leader fails.

## 🧰 Prerequisites

Before running the project, ensure you have the following installed: 

- Docker (Docker Desktop)
- Kubernetes (kubectl & Minikube)
- Python 3
- Visual Studio Code (recommended)

## ✨ Features

- 🍪 Random fortune cookie generator.

- 🔁 Multiple pods for fault tolerance.

- 👑 Leader election using Bully Algorithm.

- ⚡ Automatic recovery when leader pod fails.

## 🛠️ Tech Stack 

- **Frontend**: HTML, CSS, JavaScript

- **Backend**: Python 3

- **Containerization**: Docker

- **Orchestration**: Kubernetes (Deployment + Services)


## 📦 Installation & Deployment

### Installation
To run the project locally, run the following steps: 

1. **Clone the repository**
If you haven't yet, first set up Git and authentication with GitHub.com from Git. For more information, please see <a href="https://docs.github.com/en/get-started/git-basics/set-up-git">Set up Git</a>. Click on <> Code and copy the URL of the repository that should look like the following:  

```bash
   git clone https://github.com/au706600/Project-2-kubernetes.git
```

2. **Open Git Bash in whatever local file location in your computer and run the following**

```bash
   git clone https://github.com/au706600/Project-2-kubernetes.git
   cd Project-2-kubernetes
```

3. **Install Dependencies**
Make sure you have pip installed. Then install packages: 
```bash
   pip install
```

### Deployment

1. **Start minikube by running the following command in cmd**

```
minikube start
```

2. **Navigate to where your project directory is located on your computer and build the docker image**

```
docker build -t <name of dockerimage>
```

3. **Apply the configuration files**
```
kubectl apply -f Deployment.yml
kubectl apply -f Services.yml
```


## 🧱 Directory Structure

```
├── Deployment.yml 
├── FortuneCookies.txt
├── KubernetesCookies.css
├── README.md
├── Services.yml
├── bully-algorithm.py
├── dockerfile
├── generateArrayFromTextFile.py
├── index.html
└── requirements.txt
```

## 🎥 Demo


## ⚠️ Issues/Problems

- Currently, after running the Dockerfile and applying the Kubernetes configuration files (Deployment.yml and Services.yml), the pods do not reach the READY state, when running the following command:
```
kubectl get pods
```

This is likely due to configuration issues in the Deployment or Service definition (e.g. container start-up delays or networking between pods).

As a result, the website is not accessible and hence isn't served, which makes it difficult to test the Bully-algorithm. 

- However we can test to see, if a pod can be connected to the port 8000 with our html website in a kubernetes cluster, which we have set manually. The command to forward a pod name to select a matching port
to forward to is port-forwarding, which forwards from ip-address that the kubernetes-cluster is running to the port, we have set manually:

```
kubectl port-forward pod/<pod-name> 8000:8000
```

The names of the pods are shown, when running the command as stated above: 

```
kubectl get pods
```
