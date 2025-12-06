# Stress Testing Harness

This directory contains a comprehensive stress testing harness for the mini_transcriber concurrent request handling system.

## Overview

The stress test harness:
- ✅ Simulates concurrent client requests
- ✅ Monitors CPU and RAM usage in real-time
- ✅ Generates detailed performance reports
- ✅ Provides hardware-specific configuration recommendations
- ✅ Tests both sync and async modes
- ✅ Can be run on any machine with the service

## Quick Start

### 1. Install Dependencies

```bash
pip install psutil requests
```

### 2. Start the Service

```bash
# In one terminal
python app.py
```

### 3. Run Stress Test

```bash
# In another terminal
python tests/stress_test.py
```

## Usage

### Basic Usage

```bash
# Run with defaults (10 workers, 30 seconds)
python tests/stress_test.py

# Custom configuration
python tests/stress_test.py --workers 20 --duration 60

# Test async mode
python tests/stress_test.py --async-mode

# Save report to file
python tests/stress_test.py --output report.json
```

### Command-Line Options

```
--url URL            Base URL of service (default: http://127.0.0.1:8080)
--workers N          Number of concurrent test workers (default: 10)
--duration SECONDS   Test duration in seconds (default: 30)
--async-mode         Use async mode (?async=true)
--output FILE        Output JSON report to file
```

## Understanding the Report

### Request Statistics

- **Total Requests**: Number of requests submitted during test
- **Successful (200)**: Requests that completed successfully
- **Queued (202)**: Requests accepted in async mode
- **Service Busy (503)**: Requests rejected due to full queue
- **Errors**: Failed requests (timeouts, connection errors, etc.)

### Timing Statistics

- **Avg Duration**: Average time to process a request
- **Min/Max Duration**: Fastest and slowest requests
- **Requests/sec**: Throughput of the system

### Performance Metrics

- **CPU Usage**: Average and peak CPU utilization
- **Memory Usage**: Average and peak memory consumption (MB and %)

### Recommendations

The harness automatically analyzes results and provides:
- CPU-based recommendations for MAX_CONCURRENT_TRANSCRIPTIONS
- Memory-based warnings if usage is high
- Queue size recommendations based on rejection rate
- Specific environment variable settings for your hardware

## Example Report

```
======================================================================
STRESS TEST REPORT
======================================================================

Test Configuration:
  Duration: 30.45s
  Concurrent Workers: 10
  Base URL: http://127.0.0.1:8080

Request Statistics:
  Total Requests: 152
  Successful (200): 142 (93.4%)
  Queued (202): 0
  Service Busy (503): 10 (6.6%)
  Errors: 0

Timing Statistics:
  Avg Duration: 1.234s
  Min Duration: 0.892s
  Max Duration: 2.456s
  Requests/sec: 4.99

Performance Metrics:
  Avg CPU: 45.2%
  Max CPU: 78.3%
  Avg Memory: 156.3 MB (2.1%)
  Max Memory: 189.7 MB (2.5%)

======================================================================
RECOMMENDATIONS:
======================================================================

Based on test results:

✓  MODERATE CPU USAGE
   Current configuration is appropriate for this hardware.
   Recommendation: MAX_CONCURRENT_TRANSCRIPTIONS=1 or 2

✓  MODERATE MEMORY USAGE
   Peak memory: 190 MB
   Recommendation: Current settings are appropriate

⚠️  MODERATE REJECTION RATE
   6.6% of requests received 503 (busy)
   Recommendation: Current MAX_QUEUE_SIZE is adequate but near limit

✓  NO ERRORS
   All requests handled correctly (200, 202, or 503)

Environment variable suggestions for this hardware:
  export MAX_CONCURRENT_TRANSCRIPTIONS=2
  export MAX_QUEUE_SIZE=5
```

## Tuning for Your Hardware

### Low-End Hardware (Raspberry Pi, older laptops)
```bash
export MAX_CONCURRENT_TRANSCRIPTIONS=1
export MAX_QUEUE_SIZE=3
python tests/stress_test.py --workers 5 --duration 20
```

### Mid-Range Hardware (Modern laptops, small servers)
```bash
export MAX_CONCURRENT_TRANSCRIPTIONS=2
export MAX_QUEUE_SIZE=5
python tests/stress_test.py --workers 10 --duration 30
```

### High-End Hardware (Workstations, servers with GPU)
```bash
export MAX_CONCURRENT_TRANSCRIPTIONS=4
export MAX_QUEUE_SIZE=10
python tests/stress_test.py --workers 20 --duration 60
```

## Interpreting Results for Production

### CPU Guidelines

- **< 50% max CPU**: Increase MAX_CONCURRENT_TRANSCRIPTIONS
- **50-80% max CPU**: Current settings are optimal
- **> 80% max CPU**: Decrease MAX_CONCURRENT_TRANSCRIPTIONS or upgrade hardware

### Memory Guidelines

- **< 500 MB**: Memory is not a constraint
- **500-2000 MB**: Monitor for memory leaks
- **> 2000 MB**: Consider reducing queue size or adding more RAM

### Queue Guidelines

- **< 5% busy rate**: Queue size can be reduced
- **5-20% busy rate**: Optimal queue size
- **> 20% busy rate**: Increase MAX_QUEUE_SIZE or add more workers

### Error Guidelines

- **0% errors**: System is stable
- **< 5% errors**: Acceptable, monitor for patterns
- **> 5% errors**: Investigate error details and reduce load

## Running Tests on Different Machines

You can run the stress test on a different machine from where the service is running:

```bash
# On machine A: Run the service
python app.py

# On machine B: Run stress test pointing to machine A
python tests/stress_test.py --url http://machine-a-ip:8080
```

This is useful for:
- Testing production deployments
- Separating test load from service load
- Simulating real-world network conditions

## Continuous Integration

You can integrate stress testing into CI/CD:

```bash
# Start service in background
python app.py &
SERVICE_PID=$!

# Wait for service to start
sleep 5

# Run stress test
python tests/stress_test.py --duration 15 --output ci-report.json

# Check exit code (0 = success, 1 = too many errors)
TEST_RESULT=$?

# Kill service
kill $SERVICE_PID

# Exit with test result
exit $TEST_RESULT
```

## Troubleshooting

### "Cannot connect to service"
- Ensure `python app.py` is running
- Check the URL is correct (default: http://127.0.0.1:8080)
- Verify firewall settings if testing remotely

### High error rate
- Service may be overloaded - reduce --workers
- Check service logs for errors
- Ensure whisper model is downloaded

### Test takes too long
- Reduce --duration
- Reduce --workers
- Use --async-mode for faster results

## Advanced Usage

### Testing with Custom Audio
Edit `create_test_audio()` in stress_test.py to use real audio files.

### Custom Metrics
Add additional monitoring in `monitor_performance()` method.

### Automated Tuning
Run multiple tests with different configurations to find optimal settings:

```bash
for workers in 1 2 3 4; do
    export MAX_CONCURRENT_TRANSCRIPTIONS=$workers
    python tests/stress_test.py --output "report_workers_${workers}.json"
done
```

## Support

For issues or questions:
1. Check service logs: `tail -f server.log`
2. Review /health endpoint: `curl http://127.0.0.1:8080/health`
3. Enable debug mode in stress_test.py
4. Review error_details in the report
