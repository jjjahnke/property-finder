# System Specification: High-Performance GPU Entity Resolution Pipeline

**Project Name:** Parcel-Event Reconciliation System
**Version:** 1.0.0
**Date:** December 04, 2025
**Author:** Technical Architecture Team

---

## 1. Executive Summary
This project aims to resolve data discrepancies between a "Clean" State Parcel Dataset (Structured) and a "Dirty" Event Dataset (Unstructured) using a local, GPU-accelerated RAG (Retrieval Augmented Generation) architecture.

The system utilizes a **Hybrid Hardware Strategy** to optimize throughput and latency:
* **Batch Indexing:** Offloaded to legacy Tesla P100 GPUs (High Throughput, FP32).
* **Inference & Logic:** Handled by modern RTX 4000 Ada GPUs (Tensor Cores, BF16/FP8).
* **Storage:** In-Memory Vector Database (RAM-Disk) backed by Ceph Cold Storage.

---

## 2. Hardware & Infrastructure Roles

### 2.1 Server A: "The Factory" (Indexing Cluster)
* **Hardware:** 4x NVIDIA Tesla P100 (16GB VRAM each).
* **Primary Role:** High-volume vector embedding.
* **Constraint:** Compute Capability 6.0 (No Tensor Cores). Must use direct Python execution (no vLLM/Ollama).
* **Throughput Goal:** ~3,000 records/sec via parallel sharding.

### 2.2 Server B: "The Lab" (Intelligence Cluster)
* **Hardware:** 2x NVIDIA RTX 4000 Ada Generation.
* **Memory:** 244 GB System RAM.
* **Primary Role:**
    1.  **Vector Hosting:** Hosting the entire index in RAM.
    2.  **Agent Inference:** Running Llama-3-8B-Instruct via vLLM.
* **Latency Goal:** <200ms Vector Retrieval, <3s LLM Reasoning.

---

## 3. Component Architecture

### Component A: The Indexing Service
**Type:** Kubernetes Job (`completionMode: Indexed`)
**Location:** Server A

* **Logic:**
    * Connects to SQL Database.
    * Selects a subset of data using **Hash-Modulo Sharding** to ensure zero overlap between the 4 GPUs.
    * Generates embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
    * Pushes vectors to Component B (Qdrant).
* **Sharding Formula (SQL):**
    ```sql
    WHERE ABS(hashtext(parcel_id)) % 4 = {JOB_COMPLETION_INDEX}
    ```

### Component B: The Vector Store
**Type:** Kubernetes Deployment
**Location:** Server B (Pinned to High-RAM Node)

* **Software:** Qdrant (Rust-based).
* **Storage Engine:** **RAM-Only** (`emptyDir: Memory`).
    * *Justification:* 5MM records require ~20GB RAM. Server has 244GB. RAM is 100x faster than disk.
* **Persistence Strategy (Cold Storage):**
    * **Startup:** InitContainer copies Snapshot from Ceph PVC -> RAM Disk.
    * **Backup:** Scheduled script triggers Snapshot to RAM -> Copies to Ceph PVC.

### Component C: The Detective Agent
**Type:** Kubernetes Deployment (Async Worker)
**Location:** Server B

* **Software:** Python (AsyncIO), OpenAI Client (talking to vLLM).
* **Workflow:**
    1.  **Retrieve:** Fetch unmatched event from SQL.
    2.  **Embed:** Convert event text to vector (Locally on RTX).
    3.  **Search:** Query Qdrant for Top 5 "Suspect" Parcels.
    4.  **Reason:** Send Event + Suspects to Llama 3.
    5.  **Commit:** Update SQL with Match ID and Confidence Score.

---

## 4. Kubernetes Configurations

### 4.1 Indexer Job (Server A)
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: p100-indexer
spec:
  completions: 4
  parallelism: 4
  completionMode: Indexed
  template:
    spec:
      nodeSelector:
        kubernetes.io/hostname: "server-p100"
      containers:
      - name: indexer
        image: private-registry/indexer:v1
        resources:
          limits:
            [nvidia.com/gpu](https://nvidia.com/gpu): 1
        env:
        - name: TOTAL_SHARDS
          value: "4"
        - name: DB_HOST
          value: "postgres-service"
        - name: QDRANT_HOST
          value: "qdrant-service"
```

### 4.2 Qdrant RAM-Disk Deployment (Server B)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qdrant
spec:
  replicas: 1
  template:
    spec:
      nodeSelector:
        kubernetes.io/hostname: "server-rtx-ada"
      # Init Container: Hydrates RAM from Ceph
      initContainers:
      - name: data-loader
        image: busybox
        command: ["sh", "-c", "if [ -f /ceph/snapshot ]; then cp -a /ceph/* /ram/; fi"]
        volumeMounts:
        - name: ram-disk
          mountPath: /ram
        - name: ceph-storage
          mountPath: /ceph
      containers:
      - name: qdrant
        image: qdrant/qdrant:latest
        resources:
          limits:
            memory: "64Gi"
        env:
        - name: QDRANT__STORAGE__ON_DISK_PAYLOAD
          value: "false"
        volumeMounts:
        - name: ram-disk
          mountPath: /qdrant/storage
      volumes:
      - name: ram-disk
        emptyDir:
          medium: Memory
      - name: ceph-storage
        persistentVolumeClaim:
          claimName: qdrant-ceph-pvc
```

---

## 5. Agent Logic Specification

### 5.1 LLM Prompt Template
**Model:** Meta-Llama-3-8B-Instruct (Quantized for RTX Ada)

**System Instruction:**
> You are a precise Data Reconciliation Agent. You analyze property records to find matches. You output ONLY valid JSON.

**User Prompt:**
```text
DIRTY EVENT:
ID: "{raw_id}"
Address: "{raw_address}"
Owner: "{raw_owner}"

CANDIDATES (From Vector Search):
{candidates_list}

INSTRUCTIONS:
1. Compare the Dirty Event against candidates.
2. Look for ID patterns (prefixes/suffixes) and address fuzzy matches.
3. If a match is found, return the Parcel ID.
4. If no match is confident, set "match_found": false.

OUTPUT FORMAT:
{
  "match_found": boolean,
  "parcel_id": "string",
  "confidence": float (0.0-1.0),
  "pattern_notes": "string explanation"
}
```

---

## 6. Implementation Phases

1.  **Storage Setup:** Create Ceph PVC `qdrant-ceph-data`.
2.  **Vector Infrastructure:** Deploy Qdrant (RAM mode) and expose via ClusterIP.
3.  **Indexing:** Build `indexer.py` Docker image, run Kubernetes Job on P100s, verify 5MM vectors.
4.  **Inference:** Deploy vLLM on RTX 4000, run `detective.py` worker, monitor match rates.
