# =============================================================================
# run.py — Robust Single Script: starts backend (FastAPI) then frontend (Streamlit)
# =============================================================================
# Usage: python run.py
# Backend: http://127.0.0.1:8000
# UI: http://127.0.0.1:8501
# =============================================================================

import os
import socket
import subprocess
import sys
import time
import webbrowser
import platform

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
STREAMLIT_PORT = 8501

# Project root (where run.py lives)
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT:
    os.chdir(ROOT)

def kill_process_on_port(port: int):
    """Finds and kills any process usage (LISTENING or otherwise) on the specified port."""
    if platform.system().lower() != "windows":
        return
    try:
        # Get all PIDs using this port
        cmd = f'netstat -ano | findstr :{port}'
        output = subprocess.check_output(cmd, shell=True).decode()
        pids = set()
        for line in output.strip().split('\n'):
            parts = line.strip().split()
            if len(parts) >= 5:
                # The last part is the PID
                pid = parts[-1]
                if pid and pid != '0':
                    pids.add(pid)
        
        for pid in pids:
            print(f"Cleaning up process {pid} on port {port}...")
            subprocess.run(['taskkill', '/F', '/PID', pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if pids:
            time.sleep(1) # Wait for OS to release the socket
    except Exception:
        # Likely no processes found
        pass

def wait_for_backend(url: str, timeout: float = 60.0) -> bool:
    print(f"Waiting for backend at {url}...", end="", flush=True)
    import urllib.request
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=2) as response:
                if response.status == 200:
                    print(" Ready!")
                    return True
        except Exception:
            print(".", end="", flush=True)
            time.sleep(1)
    print(" Timeout.")
    return False

def main():
    print("🚀 Starting OmniTutor AI...")
    
    # 1. Clean up existing processes on our target ports
    kill_process_on_port(BACKEND_PORT)
    kill_process_on_port(STREAMLIT_PORT)
    
    # Extra safety: kill any other stray python/uvicorn processes related to this project
    # (Optional, but helps if they aren't on specific ports yet)

    # 2. Start Backend
    backend_url = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
    backend_cmd = [
        sys.executable,
        "-m", "uvicorn",
        "app.main:app",
        "--host", BACKEND_HOST,
        "--port", str(BACKEND_PORT),
    ]
    
    env = os.environ.copy()
    env["BACKEND_URL"] = backend_url
    
    print(f"Starting backend on {backend_url}...")
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # Capture both to show on failure
        text=True,
    )

    # 3. Wait for Backend
    # Note: Since we are piping stdout, we might need to read it to prevent deadlock,
    # but for startup check uvicorn doesn't produce enough output to fill the buffer usually.
    # However, to be safe, we'll wait in a separate thread if needed or just use a short wait.
    
    ready = wait_for_backend(backend_url)
    
    if not ready:
        print("❌ Backend failed to start within timeout.")
        # Try to show why
        try:
            # Non-blocking check for any output
            if backend_proc.poll() is not None:
                output, _ = backend_proc.communicate(timeout=1)
                print("Exit Output:\n", output)
        except Exception:
            pass
        backend_proc.terminate()
        sys.exit(1)

    # 4. Start UI
    streamlit_cmd = [
        sys.executable,
        "-m", "streamlit",
        "run", "streamlit_app.py",
        "--server.port", str(STREAMLIT_PORT),
        "--server.address", "127.0.0.1",
        "--browser.gatherUsageStats", "false",
    ]
    
    front_env = os.environ.copy()
    front_env["BACKEND_URL"] = backend_url
    
    print(f"Starting streamlit UI on http://127.0.0.1:{STREAMLIT_PORT}...")
    
    # Automatically open browser
    try:
        def open_browser():
            time.sleep(3) # Wait for streamlit to be surely up
            webbrowser.open(f"http://127.0.0.1:{STREAMLIT_PORT}")
        
        import threading
        threading.Thread(target=open_browser, daemon=True).start()
    except Exception:
        pass

    try:
        # We don't pipe UI output so it goes to console as usual
        subprocess.run(streamlit_cmd, cwd=ROOT, env=front_env)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if backend_proc:
            backend_proc.terminate()
            backend_proc.wait(timeout=5)

if __name__ == "__main__":
    main()
