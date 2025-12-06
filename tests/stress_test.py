#!/usr/bin/env python3
"""
Stress test harness for mini_transcriber concurrent request handling.

This test suite stresses the transcription service with concurrent requests
and monitors CPU/RAM usage to help tune configuration for specific hardware.

Usage:
    python tests/stress_test.py
    
Environment variables:
    MAX_CONCURRENT_TRANSCRIPTIONS - Number of concurrent workers (default: 1)
    MAX_QUEUE_SIZE - Maximum queue size (default: 5)
    STRESS_TEST_DURATION - Test duration in seconds (default: 30)
    STRESS_TEST_WORKERS - Number of concurrent test clients (default: 10)
"""

import os
import sys
import time
import psutil
import threading
import requests
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import io

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class StressTestResult:
    """Results from a single request."""
    request_id: int
    start_time: float
    end_time: float
    duration: float
    status_code: int
    response_data: Dict[str, Any]
    error: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """System performance metrics at a point in time."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float


class StressTestHarness:
    """Stress testing harness for transcription service."""
    
    def __init__(self, 
                 base_url: str = "http://127.0.0.1:8080",
                 num_workers: int = 10,
                 duration_seconds: int = 30):
        self.base_url = base_url
        self.num_workers = num_workers
        self.duration_seconds = duration_seconds
        self.results: List[StressTestResult] = []
        self.performance_metrics: List[PerformanceMetrics] = []
        self.stop_monitoring = False
        self.process = psutil.Process()
        
    def create_test_audio(self) -> bytes:
        """Create minimal valid WAV file for testing."""
        # Minimal 16-bit PCM WAV header + 1 second of silence at 16kHz
        sample_rate = 16000
        num_samples = sample_rate  # 1 second
        bits_per_sample = 16
        num_channels = 1
        
        # WAV header
        data = bytearray()
        data += b'RIFF'
        data += (36 + num_samples * num_channels * (bits_per_sample // 8)).to_bytes(4, 'little')
        data += b'WAVE'
        data += b'fmt '
        data += (16).to_bytes(4, 'little')  # Subchunk1Size
        data += (1).to_bytes(2, 'little')   # AudioFormat (PCM)
        data += num_channels.to_bytes(2, 'little')
        data += sample_rate.to_bytes(4, 'little')
        data += (sample_rate * num_channels * bits_per_sample // 8).to_bytes(4, 'little')
        data += (num_channels * bits_per_sample // 8).to_bytes(2, 'little')
        data += bits_per_sample.to_bytes(2, 'little')
        data += b'data'
        data += (num_samples * num_channels * (bits_per_sample // 8)).to_bytes(4, 'little')
        
        # Silent audio data (zeros)
        data += bytes(num_samples * num_channels * (bits_per_sample // 8))
        
        return bytes(data)
    
    def monitor_performance(self):
        """Monitor CPU and memory usage in background thread."""
        while not self.stop_monitoring:
            try:
                cpu = self.process.cpu_percent(interval=0.1)
                mem_info = self.process.memory_info()
                mem_mb = mem_info.rss / 1024 / 1024
                mem_percent = self.process.memory_percent()
                
                metric = PerformanceMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu,
                    memory_mb=mem_mb,
                    memory_percent=mem_percent
                )
                self.performance_metrics.append(metric)
                
            except Exception as e:
                print(f"Error monitoring performance: {e}")
            
            time.sleep(0.5)  # Sample every 500ms
    
    def make_request(self, request_id: int, use_async: bool = False) -> StressTestResult:
        """Make a single transcription request."""
        start_time = time.time()
        
        try:
            audio_data = self.create_test_audio()
            files = {'file': ('test.wav', io.BytesIO(audio_data), 'audio/wav')}
            
            url = f"{self.base_url}/transcribe"
            if use_async:
                url += "?async=true"
            
            response = requests.post(url, files=files, timeout=10)
            end_time = time.time()
            
            return StressTestResult(
                request_id=request_id,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                status_code=response.status_code,
                response_data=response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            )
            
        except Exception as e:
            end_time = time.time()
            return StressTestResult(
                request_id=request_id,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                status_code=0,
                response_data={},
                error=str(e)
            )
    
    def run_stress_test(self, use_async: bool = False) -> Dict[str, Any]:
        """Run stress test with specified parameters."""
        print(f"\n{'='*70}")
        print(f"Starting stress test:")
        print(f"  Base URL: {self.base_url}")
        print(f"  Workers: {self.num_workers}")
        print(f"  Duration: {self.duration_seconds}s")
        print(f"  Mode: {'Async' if use_async else 'Sync'}")
        print(f"{'='*70}\n")
        
        # Start performance monitoring
        self.stop_monitoring = False
        monitor_thread = threading.Thread(target=self.monitor_performance, daemon=True)
        monitor_thread.start()
        
        # Run stress test
        test_start = time.time()
        request_count = 0
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            
            # Submit requests for the duration
            while time.time() - test_start < self.duration_seconds:
                future = executor.submit(self.make_request, request_count, use_async)
                futures.append(future)
                request_count += 1
                time.sleep(0.1)  # Small delay between submissions
            
            # Wait for all requests to complete
            print(f"Submitted {request_count} requests, waiting for completion...")
            for future in as_completed(futures):
                result = future.result()
                self.results.append(result)
        
        # Stop monitoring
        self.stop_monitoring = True
        monitor_thread.join(timeout=2)
        
        test_end = time.time()
        
        return self.generate_report(test_start, test_end)
    
    def generate_report(self, test_start: float, test_end: float) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_requests = len(self.results)
        successful = [r for r in self.results if r.status_code == 200]
        queued = [r for r in self.results if r.status_code == 202]
        busy = [r for r in self.results if r.status_code == 503]
        errors = [r for r in self.results if r.status_code not in (200, 202, 503) or r.error]
        
        # Calculate statistics
        if successful:
            avg_duration = sum(r.duration for r in successful) / len(successful)
            min_duration = min(r.duration for r in successful)
            max_duration = max(r.duration for r in successful)
        else:
            avg_duration = min_duration = max_duration = 0
        
        # Performance metrics
        if self.performance_metrics:
            avg_cpu = sum(m.cpu_percent for m in self.performance_metrics) / len(self.performance_metrics)
            max_cpu = max(m.cpu_percent for m in self.performance_metrics)
            avg_mem = sum(m.memory_mb for m in self.performance_metrics) / len(self.performance_metrics)
            max_mem = max(m.memory_mb for m in self.performance_metrics)
            avg_mem_pct = sum(m.memory_percent for m in self.performance_metrics) / len(self.performance_metrics)
            max_mem_pct = max(m.memory_percent for m in self.performance_metrics)
        else:
            avg_cpu = max_cpu = avg_mem = max_mem = avg_mem_pct = max_mem_pct = 0
        
        report = {
            'test_info': {
                'duration_seconds': test_end - test_start,
                'num_workers': self.num_workers,
                'base_url': self.base_url
            },
            'request_stats': {
                'total_requests': total_requests,
                'successful_200': len(successful),
                'queued_202': len(queued),
                'busy_503': len(busy),
                'errors': len(errors),
                'success_rate': len(successful) / total_requests * 100 if total_requests > 0 else 0,
                'busy_rate': len(busy) / total_requests * 100 if total_requests > 0 else 0
            },
            'timing_stats': {
                'avg_duration_seconds': avg_duration,
                'min_duration_seconds': min_duration,
                'max_duration_seconds': max_duration,
                'requests_per_second': total_requests / (test_end - test_start) if test_end > test_start else 0
            },
            'performance_stats': {
                'avg_cpu_percent': avg_cpu,
                'max_cpu_percent': max_cpu,
                'avg_memory_mb': avg_mem,
                'max_memory_mb': max_mem,
                'avg_memory_percent': avg_mem_pct,
                'max_memory_percent': max_mem_pct
            },
            'error_details': [
                {
                    'request_id': r.request_id,
                    'status_code': r.status_code,
                    'error': r.error,
                    'response': r.response_data
                }
                for r in errors[:10]  # First 10 errors
            ]
        }
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """Print formatted test report."""
        print(f"\n{'='*70}")
        print("STRESS TEST REPORT")
        print(f"{'='*70}\n")
        
        print("Test Configuration:")
        print(f"  Duration: {report['test_info']['duration_seconds']:.2f}s")
        print(f"  Concurrent Workers: {report['test_info']['num_workers']}")
        print(f"  Base URL: {report['test_info']['base_url']}")
        
        print("\nRequest Statistics:")
        stats = report['request_stats']
        print(f"  Total Requests: {stats['total_requests']}")
        print(f"  Successful (200): {stats['successful_200']} ({stats['success_rate']:.1f}%)")
        print(f"  Queued (202): {stats['queued_202']}")
        print(f"  Service Busy (503): {stats['busy_503']} ({stats['busy_rate']:.1f}%)")
        print(f"  Errors: {stats['errors']}")
        
        print("\nTiming Statistics:")
        timing = report['timing_stats']
        print(f"  Avg Duration: {timing['avg_duration_seconds']:.3f}s")
        print(f"  Min Duration: {timing['min_duration_seconds']:.3f}s")
        print(f"  Max Duration: {timing['max_duration_seconds']:.3f}s")
        print(f"  Requests/sec: {timing['requests_per_second']:.2f}")
        
        print("\nPerformance Metrics:")
        perf = report['performance_stats']
        print(f"  Avg CPU: {perf['avg_cpu_percent']:.1f}%")
        print(f"  Max CPU: {perf['max_cpu_percent']:.1f}%")
        print(f"  Avg Memory: {perf['avg_memory_mb']:.1f} MB ({perf['avg_memory_percent']:.1f}%)")
        print(f"  Max Memory: {perf['max_memory_mb']:.1f} MB ({perf['max_memory_percent']:.1f}%)")
        
        if report['error_details']:
            print("\nError Details (first 10):")
            for err in report['error_details']:
                print(f"  Request #{err['request_id']}: Status {err['status_code']}")
                if err['error']:
                    print(f"    Error: {err['error']}")
                if err['response']:
                    print(f"    Response: {err['response']}")
        
        print(f"\n{'='*70}")
        print("RECOMMENDATIONS:")
        print(f"{'='*70}\n")
        
        # Generate recommendations
        self.print_recommendations(report)
    
    def print_recommendations(self, report: Dict[str, Any]):
        """Print hardware-specific recommendations."""
        perf = report['performance_stats']
        stats = report['request_stats']
        
        print("Based on test results:\n")
        
        # CPU recommendations
        if perf['max_cpu_percent'] > 90:
            print("⚠️  HIGH CPU USAGE DETECTED")
            print("   Current configuration may be too aggressive for this hardware.")
            print("   Recommendation: Keep MAX_CONCURRENT_TRANSCRIPTIONS=1")
        elif perf['max_cpu_percent'] > 70:
            print("✓  MODERATE CPU USAGE")
            print("   Current configuration is appropriate for this hardware.")
            print("   Recommendation: MAX_CONCURRENT_TRANSCRIPTIONS=1 or 2")
        else:
            print("✓  LOW CPU USAGE")
            print("   Hardware can handle more concurrent transcriptions.")
            print("   Recommendation: Consider MAX_CONCURRENT_TRANSCRIPTIONS=2-4")
        
        print()
        
        # Memory recommendations
        if perf['max_memory_mb'] > 2000:
            print("⚠️  HIGH MEMORY USAGE DETECTED")
            print(f"   Peak memory: {perf['max_memory_mb']:.0f} MB")
            print("   Recommendation: Monitor for memory leaks, keep queue small")
        elif perf['max_memory_mb'] > 500:
            print("✓  MODERATE MEMORY USAGE")
            print(f"   Peak memory: {perf['max_memory_mb']:.0f} MB")
            print("   Recommendation: Current settings are appropriate")
        else:
            print("✓  LOW MEMORY USAGE")
            print(f"   Peak memory: {perf['max_memory_mb']:.0f} MB")
            print("   Recommendation: Memory is not a constraint")
        
        print()
        
        # Queue recommendations
        if stats['busy_rate'] > 50:
            print("⚠️  HIGH REJECTION RATE")
            print(f"   {stats['busy_rate']:.1f}% of requests received 503 (busy)")
            print("   Recommendation: Increase MAX_QUEUE_SIZE or reduce request rate")
        elif stats['busy_rate'] > 10:
            print("⚠️  MODERATE REJECTION RATE")
            print(f"   {stats['busy_rate']:.1f}% of requests received 503 (busy)")
            print("   Recommendation: Current MAX_QUEUE_SIZE is adequate but near limit")
        else:
            print("✓  LOW REJECTION RATE")
            print(f"   {stats['busy_rate']:.1f}% of requests received 503 (busy)")
            print("   Recommendation: MAX_QUEUE_SIZE can be reduced if needed")
        
        print()
        
        # Error handling recommendations
        if stats['errors'] > 0:
            print("⚠️  ERRORS DETECTED")
            print(f"   {stats['errors']} requests failed")
            print("   Recommendation: Review error details above")
        else:
            print("✓  NO ERRORS")
            print("   All requests handled correctly (200, 202, or 503)")
        
        print()
        print("Environment variable suggestions for this hardware:")
        
        if perf['max_cpu_percent'] > 80:
            print("  export MAX_CONCURRENT_TRANSCRIPTIONS=1")
        elif perf['max_cpu_percent'] > 50:
            print("  export MAX_CONCURRENT_TRANSCRIPTIONS=2")
        else:
            print("  export MAX_CONCURRENT_TRANSCRIPTIONS=3")
        
        if stats['busy_rate'] > 30:
            print("  export MAX_QUEUE_SIZE=10")
        elif stats['busy_rate'] > 10:
            print("  export MAX_QUEUE_SIZE=7")
        else:
            print("  export MAX_QUEUE_SIZE=5")
        
        print()


def main():
    """Main entry point for stress testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Stress test mini_transcriber service')
    parser.add_argument('--url', default='http://127.0.0.1:8080',
                       help='Base URL of service (default: http://127.0.0.1:8080)')
    parser.add_argument('--workers', type=int, default=10,
                       help='Number of concurrent test workers (default: 10)')
    parser.add_argument('--duration', type=int, default=30,
                       help='Test duration in seconds (default: 30)')
    parser.add_argument('--async-mode', action='store_true',
                       help='Use async mode (?async=true)')
    parser.add_argument('--output', help='Output JSON report to file')
    
    args = parser.parse_args()
    
    # Check if service is running
    try:
        response = requests.get(f"{args.url}/health", timeout=5)
        if response.status_code != 200:
            print(f"ERROR: Service at {args.url} returned status {response.status_code}")
            print("Please start the service first: python app.py")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Cannot connect to service at {args.url}")
        print(f"Details: {e}")
        print("\nPlease start the service first: python app.py")
        sys.exit(1)
    
    print(f"✓ Service is running at {args.url}")
    
    # Run stress test
    harness = StressTestHarness(
        base_url=args.url,
        num_workers=args.workers,
        duration_seconds=args.duration
    )
    
    report = harness.run_stress_test(use_async=args.async_mode)
    harness.print_report(report)
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n✓ Report saved to {args.output}")
    
    # Exit with error code if there were significant issues
    if report['request_stats']['errors'] > report['request_stats']['total_requests'] * 0.1:
        sys.exit(1)  # More than 10% errors
    
    sys.exit(0)


if __name__ == '__main__':
    main()
