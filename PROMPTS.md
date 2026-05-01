# 🛠️ Engineering Process: Prompts, Specs & Plans

This document provides a transparent look into the development of the **Incident Management System (IMS)**. It tracks the logical progression from architectural requirements to final implementation and stress testing.

---

## 🏗️ Phase 1: Architecture & Requirements Analysis
**Objective:** Translate the assignment's mission-critical requirements into a scalable technical stack.

**Primary Prompt:**
> "I am building a mission-critical Incident Management System (IMS) for an SRE internship assignment. The system must handle up to 10,000 signals/sec and include an asynchronous ingestion layer. Propose a backend architecture using FastAPI, Redis (for debouncing), MongoDB (for raw logs), and PostgreSQL (for structured incidents). Explain how the system will handle backpressure."[cite: 1]

**Outcome:**
*   Designed a **Producer-Consumer** architecture using Redis RQ to decouple the API from the database.[cite: 1]
*   Identified the need for a **Data Lake** (MongoDB) to store high-volume audit logs without slowing down the primary workflow.[cite: 1]

---

## 📊 Phase 2: Data Modeling & Patterns
**Objective:** Implement robust design patterns to manage complexity and ensure a transactional "Source of Truth."[cite: 1]

**Prompt:**
> "How can I implement a strict incident lifecycle (OPEN → INVESTIGATING → RESOLVED → CLOSED) while ensuring an incident cannot be CLOSED without a Root Cause Analysis (RCA)? Suggest a design pattern for this and for severity classification (P0 for RDBMS, P1 for API, P2 for Cache)."[cite: 1]

**Outcome:**
*   Implemented the **State Pattern** (`state.py`) to enforce valid transitions and RCA requirements.[cite: 1]
*   Implemented the **Strategy Pattern** (`strategy.py`) for automatic severity classification based on component type.[cite: 1]

---

## ⚡ Phase 3: Reliability & Performance Engineering
**Objective:** Address the "Resilience" criteria, specifically debouncing and backpressure handling.[cite: 1]

**Prompt:**
> "I need to implement a Redis-based debouncing logic. If 100 signals arrive for the same 'Component ID' within 10 seconds, only one Incident should be created in PostgreSQL, but all 100 raw signals must be logged in MongoDB. Write a Python worker function for this."[cite: 1]

**Outcome:**
*   Created `worker.py` with a 10-second debounce window logic.[cite: 1]
*   Added retry logic for database writes to handle transient failures.[cite: 1]

---

## 🐳 Phase 4: DevOps & Containerization
**Objective:** Ensure a "running application" with secure, lean packaging.[cite: 1]

**Prompt:**
> "Create a multi-stage Dockerfile for a FastAPI and RQ worker system. The image should be secure, run as a non-root user, and use python:3.10-slim. Provide a docker-compose.yml to orchestrate the backend, worker, Redis, PostgreSQL, and MongoDB."[cite: 1]

**Outcome:**
*   Produced a secure, multi-stage build that minimizes the attack surface by removing build tools from the final image.[cite: 1]

---

## 🧪 Phase 5: Simulation & Verification
**Objective:** Prove the system's ability to handle high-volume bursts and failure scenarios.[cite: 1]

**Prompt:**
> "Write a simulation script (`simulate.py`) that uses threading to send synthetic alert signals. I need to test three scenarios: Normal Load (300 signals), an RDBMS Failure Storm (200 signals), and a High Burst (700 signals). The worker should print throughput metrics every 5 seconds."[cite: 1]

**Outcome:**
*   Developed a stress-test suite that verifies the system's performance metrics and status transition logic under load.[cite: 1]
