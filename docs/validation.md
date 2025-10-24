Here is a step-by-step debugging guide for your LiveKit SIP and Agent setup, from the most basic network checks to advanced real-time call tracing.

-----

## 1\. Basic VM & Network Debugging

First, make sure your services can communicate.

### `ss` (Socket Statistics)

  * **Command:** `ss -tulpn | grep -E '7880|6379|5060'`
  * **What to Look For:**
      * You need to see `LISTEN` states for your critical ports.
      * This confirms your services *are running* and have successfully bound to their ports.
    <!-- end list -->
    ```bash
    tcp   LISTEN   0   4096   0.0.0.0:6379      0.0.0.0:* users:(("redis-server",...))
    tcp   LISTEN   0   4096   0.0.0.0:7880      0.0.0.0:* users:(("livekit-server",...))
    udp   LISTEN   0   4096   0.0.0.0:5060      0.0.0.0:* users:(("livekit-sip",...))
    ```
  * **What to Do:**
      * **If a port is missing:** That service is not running. For example, if `7880` is missing, your `livekit-server` is down.
      * **If the IP is `127.0.0.1` (localhost):** The service is only listening for local connections. Other machines (like your agent) won't be able to connect. You must configure it to listen on `0.0.0.0` or your VM's public/private IP.

### `ping`

  * **Command:**
      * From your VM: `ping <IP_OF_YOUR_AGENT_MACHINE>`
      * From your Agent machine: `ping <IP_OF_YOUR_VM>`
  * **What to Look For:** A continuous reply of `64 bytes from ... time=... ms`.
  * **What to Do:**
      * **If you get "Request timed out" or "Destination Host Unreachable":** There is a fundamental network block between your machines. This is a **firewall** problem (on the VM or your cloud provider) or a routing issue. LiveKit will not work until this is fixed.

-----

## 2\. Core Service Status

Check that the server processes themselves are running and healthy.

### `redis-cli`

  * **Command:** `redis-cli ping`
  * **What to Look For:**
    ```
    PONG
    ```
  * **What to Do:**
      * **If it says "Could not connect to Redis at ...":** Your `livekit-server` and `livekit-sip` cannot start. Make sure Redis is running (`sudo systemctl status redis-server`) and listening on the correct IP/port.

### `ps aux` (Process Status)

  * **Command:** `ps aux | grep livekit-server`
  * **What to Look For:** A process line showing your server is running.
    ```bash
    root  1234  ...  livekit-server --config /path/to/livekit.yaml
    ```
  * **What to Do:** If no process is found, your server crashed or failed to start. Check its logs for errors (likely a Redis connection failure or a bad `.yaml` config).

### `ps aux` (Agent Worker)

  * **Command:** `ps aux | grep cagent.py`
  * **What to Look For:** The process for your Python agent.
    ```bash
    user  5678  ...  python cagent.py dev
    ```
  * **What to Do:**
      * **CRITICAL:** If you see **multiple** `cagent.py` processes, you have "ghost" workers. This will cause unpredictable behavior (like the old worker with the blank `agentName` taking the job).
      * **Action:** Kill all of them. Find their Process IDs (PIDs) and run `kill -9 <PID_NUMBER>`. Then start your agent *one* time.

-----

## 3\. LiveKit Configuration

Verify what the LiveKit server *thinks* its configuration is.

### `lk sip inbound list`

  * **Command:** `lk sip inbound list`
  * **What to Look For:**
      * Your list of trunks. Find the trunk ID from your logs (e.g., `ST_CSFtgGo4bhHe`).
      * Check the `numbers`, `allowed_addresses`, `username`, and `password` fields.
    <!-- end list -->
    ```json
    {
      "sip_trunk_id": "ST_CSFtgGo4bhHe",
      "name": "My-Trunk",
      "username": "cisco",
      "password": "...",
      ...
    }
    ```
  * **What to Do:**
      * This is the fix for your **"Authentication failed - response mismatch"** error.
      * The `username` and `password` shown here **MUST** exactly match what you have entered in your Zoiper / SIP client.

### `lk sip dispatch list`

  * **Command:** `lk sip dispatch list`
  * **What to Look For:**
      * Your dispatch rule (e.g., "Friday Individual Caller Rule V2").
      * **`trunk_ids`:** Does this list include your inbound trunk ID (e.g., `ST_CSFtgGo4bhHe`)?
      * **`agentName`:** Does this *exactly* match the `agent_name` in your `cagent.py`'s `WorkerOptions`? (e.g., `friday-assistant`).
    <!-- end list -->
    ```json
    {
      "sip_dispatch_rule_id": "DR_...",
      "name": "Friday Individual Caller Rule V2",
      "trunk_ids": [
        "ST_CSFtgGo4bhHe"
      ],
      ...
      "room_config": {
        "agents": [
          {
            "agent_name": "friday-assistant"
          }
        ]
      }
    }
    ```
  * **What to Do:** If there is any mismatch, the server will never find your agent. Use `lk sip dispatch update` to fix it.

-----

## 4\. Real-time Log Tailing (The Most Powerful Tool)

This is how you watch the entire flow live. You will need **two terminals** open *before* you make the call.

  * **Terminal 1 (Server Log):** `tail -f /path/to/livekit-server.log` (Or just watch the live output from running `livekit-server`)
  * **Terminal 2 (Agent Log):** `python cagent.py dev` (Or just `python cagent.py`)

Now, make a call and watch the logs.

### Step 1: Agent Registration (Before the call)

  * **Where to Look:** Terminal 1 (Server Log)
  * **What to Look For:** The *moment* you start your Python script in Terminal 2, you **MUST** see this line in Terminal 1:
    ```
    INFO   livekit.agents  ...  worker registered   {"agentName": "friday-assistant", "workerID": ...}
    ```
  * **What to Do (This is your \#1 problem):**
      * **If you see `agentName: ""`:** Your `cagent.py` is wrong. You haven't added `agent_name="friday-assistant"` to the `WorkerOptions` at the bottom of the file.
      * **If you see *nothing*:** Your agent script can't connect to the server. Go back to **Section 1 (ping, ss, firewall)**.

### Step 2: The Call (The moment you dial)

1.  **Server Log:** `INFO ... processing invite` (The call is hitting your SIP server).
2.  **Server Log:** (If auth is on) `INFO ... Authentication failed` **OR** `DEBUG ... Digest computation completed ... responsesMatch: true`. (This tells you if your password is right).
3.  **Server Log:** `INFO ... starting RTC session ... "room": "friday-call-..."` (The call is in a room).
4.  **Server Log:** `INFO ... "CreateRoom": {"agents": [{"agentName": "friday-assistant"}]}` (The server is *looking* for your agent).
5.  **Server Log (The Failure Point):**
      * **BAD:** `INFO ... not dispatching agent job since no worker is available {"agentName": "friday-assistant"}`. This means **Step 1 failed**. Your worker is not registered with the correct name.
      * **GOOD:** `INFO ... dispatching agent job ... "agentName": "friday-assistant"`
6.  **Agent Log (The Hand-off):**
      * If Step 5 was "GOOD", you will *immediately* see this in Terminal 2:
        `INFO ... received job request ... "agent_name": "friday-assistant"`
7.  **From here:** The agent takes over. If the agent crashes, you will see a `TypeError` or other Python error in Terminal 2. The call will be silent and then hang up.