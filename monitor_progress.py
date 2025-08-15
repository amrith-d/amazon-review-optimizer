#!/usr/bin/env python3
"""
Progress Monitor - Track validation progress
"""

import time
import psutil
import sys
from datetime import datetime

def monitor_validation_progress():
    """Monitor the progress of validation scripts"""
    print("📊 MONITORING VALIDATION PROGRESS")
    print("=" * 40)
    
    start_time = time.time()
    last_check = time.time()
    
    while True:
        try:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Check if Python processes are running
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        if any(script in cmdline for script in ['progressive_validation.py', 'validate_500.py']):
                            python_processes.append({
                                'pid': proc.info['pid'],
                                'script': 'progressive_validation' if 'progressive_validation' in cmdline else 'validate_500',
                                'runtime': elapsed
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Display status
            if current_time - last_check >= 30:  # Update every 30 seconds
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Elapsed: {elapsed:.0f}s")
                
                if python_processes:
                    for proc in python_processes:
                        print(f"  🔄 {proc['script']}: PID {proc['pid']} - Running {proc['runtime']:.0f}s")
                else:
                    print("  ✅ No validation processes running")
                    break
                
                last_check = current_time
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            print(f"\n⚠️ Monitoring stopped by user")
            break
        except Exception as e:
            print(f"⚠️ Monitor error: {e}")
            time.sleep(10)
    
    print(f"\n📊 Monitoring complete - Total time: {elapsed:.0f}s")

if __name__ == "__main__":
    monitor_validation_progress()