#!/usr/bin/env python3
"""
GPU Performance Monitor

Monitors GPU usage during embedding generation.
Requires: nvidia-ml-py3 (pip install nvidia-ml-py3)
"""

import time
import threading


def monitor_gpu(duration_seconds: int = 30, interval: float = 1.0):
    """
    Monitor GPU usage for specified duration.
    
    Args:
        duration_seconds: How long to monitor
        interval: Sampling interval in seconds
    """
    try:
        import pynvml
        
        # Initialize NVML
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        
        if device_count == 0:
            print("❌ No NVIDIA GPUs detected")
            return
        
        # Get first GPU
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_name = pynvml.nvmlDeviceGetName(handle)
        
        print(f"\n{'='*60}")
        print(f"GPU Monitor: {gpu_name}")
        print(f"{'='*60}")
        print(f"Duration: {duration_seconds}s, Interval: {interval}s\n")
        print(f"{'Time':>8} {'GPU %':>8} {'Memory':>12} {'Temp':>8} {'Power':>10}")
        print(f"{'-'*60}")
        
        start_time = time.time()
        samples = []
        
        try:
            while time.time() - start_time < duration_seconds:
                # Get GPU stats
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW to W
                
                # Calculate elapsed time
                elapsed = time.time() - start_time
                
                # Print stats
                memory_used_gb = memory.used / (1024**3)
                memory_total_gb = memory.total / (1024**3)
                
                print(f"{elapsed:7.1f}s {utilization.gpu:7d}% "
                      f"{memory_used_gb:5.1f}/{memory_total_gb:.1f}GB "
                      f"{temp:7d}°C {power:9.1f}W")
                
                # Store sample
                samples.append({
                    'time': elapsed,
                    'gpu_util': utilization.gpu,
                    'memory_used_gb': memory_used_gb,
                    'temp': temp,
                    'power': power
                })
                
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n⚠️ Monitoring interrupted by user")
        
        # Print summary
        if samples:
            print(f"\n{'='*60}")
            print("SUMMARY")
            print(f"{'='*60}")
            
            avg_gpu = sum(s['gpu_util'] for s in samples) / len(samples)
            max_gpu = max(s['gpu_util'] for s in samples)
            avg_mem = sum(s['memory_used_gb'] for s in samples) / len(samples)
            max_mem = max(s['memory_used_gb'] for s in samples)
            avg_temp = sum(s['temp'] for s in samples) / len(samples)
            max_temp = max(s['temp'] for s in samples)
            avg_power = sum(s['power'] for s in samples) / len(samples)
            max_power = max(s['power'] for s in samples)
            
            print(f"Samples: {len(samples)}")
            print(f"GPU Utilization: avg={avg_gpu:.1f}%, max={max_gpu}%")
            print(f"Memory Usage: avg={avg_mem:.1f}GB, max={max_mem:.1f}GB")
            print(f"Temperature: avg={avg_temp:.1f}°C, max={max_temp}°C")
            print(f"Power Usage: avg={avg_power:.1f}W, max={max_power:.1f}W")
            print(f"{'='*60}\n")
        
        # Cleanup
        pynvml.nvmlShutdown()
        
    except ImportError:
        print("❌ pynvml not installed. Install with: pip install nvidia-ml-py3")
    except Exception as e:
        print(f"❌ GPU monitoring error: {e}")


def monitor_in_background(duration_seconds: int = 30):
    """Run GPU monitor in background thread"""
    thread = threading.Thread(target=monitor_gpu, args=(duration_seconds,))
    thread.daemon = True
    thread.start()
    return thread


if __name__ == "__main__":
    import sys
    
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    monitor_gpu(duration_seconds=duration)
