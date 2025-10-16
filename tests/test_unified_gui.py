#!/usr/bin/env python3
"""
Test script für Covina Unified GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import time
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    GAP_DETECTION = "gap_detection"
    PERFORMANCE_TEST = "performance_test"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    id: str
    task_type: TaskType
    name: str
    function: callable
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    result: any = None
    error: Optional[str] = None
    callback: Optional[callable] = None


class SimpleThreadManager:
    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.running = False
        self.workers = []
        
    def start(self):
        if self.running:
            return
        self.running = True
        
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop)
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
    
    def stop(self):
        self.running = False
        for _ in range(self.max_workers):
            self.task_queue.put(None)
    
    def _worker_loop(self):
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                if task is None:
                    break
                
                task.status = TaskStatus.RUNNING
                
                try:
                    result = task.function()
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                
                if task.callback:
                    try:
                        task.callback(task)
                    except Exception as e:
                        print(f"Callback error: {e}")
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")
    
    def submit_task(self, task: Task):
        self.task_queue.put(task)


class TestGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Covina Test GUI")
        self.root.geometry("800x600")
        
        self.thread_manager = SimpleThreadManager()
        self.thread_manager.start()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main notebook
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Dashboard Tab
        dashboard_frame = ttk.Frame(notebook)
        notebook.add(dashboard_frame, text="Dashboard")
        
        ttk.Label(dashboard_frame, text="Covina Unified GUI", 
                 font=("Arial", 16, "bold")).pack(pady=20)
        
        # Quick Actions
        actions_frame = ttk.LabelFrame(dashboard_frame, text="Quick Actions")
        actions_frame.pack(pady=10, padx=20, fill=tk.X)
        
        ttk.Button(actions_frame, text="Gap Analysis", 
                  command=self.start_gap_analysis).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(actions_frame, text="Performance Test", 
                  command=self.start_performance_test).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Status
        self.status_label = ttk.Label(dashboard_frame, text="Status: Ready")
        self.status_label.pack(pady=10)
        
        # Activity Log
        log_frame = ttk.LabelFrame(dashboard_frame, text="Activity Log")
        log_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, height=10, width=80)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Gap Detection Tab
        gap_frame = ttk.Frame(notebook)
        notebook.add(gap_frame, text="Gap Detection")
        
        ttk.Label(gap_frame, text="Gap Detection System", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        ttk.Button(gap_frame, text="Start Gap Analysis", 
                  command=self.start_gap_analysis).pack(pady=5)
        
        self.gap_progress = ttk.Progressbar(gap_frame, mode='indeterminate')
        self.gap_progress.pack(pady=10, padx=20, fill=tk.X)
        
    def log_message(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def start_gap_analysis(self):
        self.log_message("Starting Gap Analysis...")
        self.status_label.config(text="Status: Running Gap Analysis")
        self.gap_progress.start()
        
        def mock_gap_analysis():
            time.sleep(3)  # Simulate processing
            return ["Gap 1: Process documentation", "Gap 2: Legal compliance"]
        
        task = Task(
            id=f"gap_{int(time.time())}",
            task_type=TaskType.GAP_DETECTION,
            name="Gap Analysis",
            function=mock_gap_analysis,
            callback=self.gap_analysis_completed
        )
        
        self.thread_manager.submit_task(task)
    
    def gap_analysis_completed(self, task: Task):
        self.root.after(0, self._gap_analysis_completed_ui, task)
    
    def _gap_analysis_completed_ui(self, task: Task):
        self.gap_progress.stop()
        self.status_label.config(text="Status: Ready")
        
        if task.status == TaskStatus.COMPLETED:
            results = task.result
            self.log_message(f"Gap Analysis completed: {len(results)} gaps found")
            for gap in results:
                self.log_message(f"  - {gap}")
        else:
            self.log_message(f"Gap Analysis failed: {task.error}")
    
    def start_performance_test(self):
        self.log_message("Starting Performance Test...")
        self.status_label.config(text="Status: Running Performance Test")
        
        def mock_performance_test():
            time.sleep(2)  # Simulate processing
            return {"database": "67,068 ops/s", "api": "951 ops/s", "grade": "A+"}
        
        task = Task(
            id=f"perf_{int(time.time())}",
            task_type=TaskType.PERFORMANCE_TEST,
            name="Performance Test",
            function=mock_performance_test,
            callback=self.performance_test_completed
        )
        
        self.thread_manager.submit_task(task)
    
    def performance_test_completed(self, task: Task):
        self.root.after(0, self._performance_test_completed_ui, task)
    
    def _performance_test_completed_ui(self, task: Task):
        self.status_label.config(text="Status: Ready")
        
        if task.status == TaskStatus.COMPLETED:
            results = task.result
            self.log_message("Performance Test completed:")
            for key, value in results.items():
                self.log_message(f"  {key}: {value}")
        else:
            self.log_message(f"Performance Test failed: {task.error}")
    
    def run(self):
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.log_message("Covina Unified GUI gestartet")
            self.root.mainloop()
        except Exception as e:
            print(f"GUI Error: {e}")
            self.thread_manager.stop()
    
    def on_closing(self):
        self.log_message("Shutting down...")
        self.thread_manager.stop()
        self.root.destroy()


if __name__ == "__main__":
    print("Starting Covina Test GUI...")
    app = TestGUI()
    app.run()