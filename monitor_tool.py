#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, scrolledtext
import asyncio
import websockets
import json
import subprocess
import os
import time
import threading
import queue

class SystemMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Linux System Monitoring Tool (Real-Time)")
        self.root.geometry("800x600")
        
        # Data queue for communication between client and GUI
        self.data_queue = queue.Queue()
        
        # Styling
        self.style = ttk.Style()
        self.style.configure("TButton", padding=5, font=("Helvetica", 10))
        self.style.configure("Header.TLabel", font=("Helvetica", 14, "bold"))
        
        # Header
        self.header = ttk.Label(root, text="Linux System Monitoring Tool", style="Header.TLabel")
        self.header.pack(pady=10)
        
        # Date/Time Label
        self.datetime_label = ttk.Label(root, text="")
        self.datetime_label.pack()
        
        # Button Frame
        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(pady=10)
        
        # Buttons
        self.categories = ["System", "CPU", "Memory", "Disk", "Network", "Processes", "Temperature"]
        for btn_text in self.categories:
            ttk.Button(self.button_frame, text=btn_text, 
                      command=lambda x=btn_text: self.display_info(x)).grid(
                          row=0, column=self.categories.index(btn_text), 
                          padx=5, pady=5)
        
        # Output Area
        self.output = scrolledtext.ScrolledText(root, width=90, height=30, 
                                              font=("Courier", 10))
        self.output.pack(pady=10)
        
        # Status Label
        self.status = ttk.Label(root, text="Starting server...")
        self.status.pack()
        
        # Data storage
        self.data = {}
        
        # Create separate event loops for server and client
        self.server_loop = asyncio.new_event_loop()
        self.client_loop = asyncio.new_event_loop()
        
        # Start WebSocket server and client in threads
        threading.Thread(target=self.run_server, daemon=True).start()
        threading.Thread(target=self.run_client, daemon=True).start()
        self.root.after(100, self.check_queue)

    def run_command(self, command):
        try:
            result = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.STDOUT)
            return result.strip()
        except subprocess.CalledProcessError as e:
            return f"Error: {e.output}"

    async def collect_data(self):
        data = {
            "datetime": time.strftime('%Y-%m-%d %H:%M:%S'),
            "system": {
                "hostname": self.run_command("hostname"),
                "os": self.run_command("cat /etc/os-release | grep PRETTY_NAME | cut -d'\"' -f2"),
                "kernel": self.run_command("uname -r"),
                "uptime": self.run_command("uptime -p")
            },
            "cpu": {
                "usage": self.run_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'"),
                "load_avg": self.run_command("uptime | awk '{print $8,$9,$10}'")
            },
            "memory": self.run_command("free -h | grep -E 'Mem:|Swap:'"),
            "disk": self.run_command("df -h | grep -E '^/dev/'"),
            "network": {
                "interfaces": self.run_command("ip -br addr"),
                "connections": self.run_command("netstat -tunap 2>/dev/null | grep ESTABLISHED | wc -l")
            },
            "processes": {
                "total": self.run_command("ps aux | wc -l"),
                "top5": self.run_command("ps -eo pid,ppid,cmd,%cpu --sort=-%cpu | head -n 6")
            },
            "temperature": self.run_command("sensors | grep -E 'Core|temp'") if self.run_command("command -v sensors") else "N/A"
        }
        return json.dumps(data)

    async def server(self, websocket, path):
        self.status.config(text="Server running, client connected")
        while True:
            data = await self.collect_data()
            await websocket.send(data)
            self.data_queue.put(json.loads(data))  # Update GUI via queue
            await asyncio.sleep(3600)  # Refresh every hour

    def run_server(self):
        asyncio.set_event_loop(self.server_loop)
        self.server_loop.create_task(websockets.serve(self.server, "localhost", 8765))
        self.server_loop.run_forever()

    async def client(self):
        uri = "ws://localhost:8765"
        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    while True:
                        message = await websocket.recv()
                        self.data_queue.put(json.loads(message))
            except (websockets.exceptions.ConnectionClosedError, ConnectionRefusedError):
                await asyncio.sleep(1)  # Retry after a delay

    def run_client(self):
        asyncio.set_event_loop(self.client_loop)
        self.client_loop.create_task(self.client())
        self.client_loop.run_forever()

    def check_queue(self):
        try:
            while not self.data_queue.empty():
                self.data = self.data_queue.get()
                self.datetime_label.config(text=f"Date: {self.data['datetime']}")
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

    def display_info(self, category):
        self.output.delete(1.0, tk.END)
        self.status.config(text=f"Displaying {category} information")
        if not self.data:
            self.output.insert(tk.END, "Waiting for initial data...\n")
            return
        
        output = f"{category} Info\n" + "-"*20 + "\n"
        if category == "System":
            output += f"Hostname: {self.data['system']['hostname']}\n"
            output += f"OS: {self.data['system']['os']}\n"
            output += f"Kernel: {self.data['system']['kernel']}\n"
            output += f"Uptime: {self.data['system']['uptime']}\n"
        elif category == "CPU":
            output += f"Usage: {self.data['cpu']['usage']}%\n"
            output += f"Load Average: {self.data['cpu']['load_avg']}\n"
        elif category == "Memory":
            output += self.data['memory']
        elif category == "Disk":
            output += self.data['disk']
        elif category == "Network":
            output += self.data['network']['interfaces'] + "\n"
            output += f"Total established connections: {self.data['network']['connections']}\n"
        elif category == "Processes":
            output += f"Total running processes: {self.data['processes']['total']}\n\n"
            output += "Top 5 CPU-consuming processes:\n" + self.data['processes']['top5']
        elif category == "Temperature":
            output += self.data['temperature'] if self.data['temperature'] != "N/A" else "Temperature sensors not available\n"
        
        self.output.insert(tk.END, output)

def main():
    root = tk.Tk()
    app = SystemMonitor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
