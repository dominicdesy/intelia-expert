"""
Test script for monitoring endpoints
"""
import asyncio
import httpx


async def test_monitoring_endpoints():
    """Test all monitoring endpoints"""

    base_url = "http://localhost:3000/api/v1/monitoring"

    print("=" * 60)
    print("MONITORING ENDPOINTS TEST")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=10.0) as client:

        # Test 1: System metrics
        print("\n[1] Testing /monitoring/system...")
        try:
            response = await client.get(f"{base_url}/system")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ System Metrics:")
                print(f"  - CPU: {data['cpu_percent']}%")
                print(f"  - Memory: {data['memory_percent']}% ({data['memory_used_gb']:.2f}GB / {data['memory_total_gb']:.2f}GB)")
                print(f"  - Disk: {data['disk_percent']}% ({data['disk_used_gb']:.2f}GB / {data['disk_total_gb']:.2f}GB)")
            else:
                print(f"✗ Failed: HTTP {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Error: {e}")

        # Test 2: Services health
        print("\n[2] Testing /monitoring/services...")
        try:
            response = await client.get(f"{base_url}/services")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Services Health:")
                for service in data:
                    status_symbol = "✓" if service['status'] == 'healthy' else "✗"
                    print(f"  {status_symbol} {service['name']}: {service['status']} ({service.get('response_time_ms', 'N/A')}ms)")
                    if service.get('error'):
                        print(f"      Error: {service['error'][:100]}...")
            else:
                print(f"✗ Failed: HTTP {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Error: {e}")

        # Test 3: Monitoring summary
        print("\n[3] Testing /monitoring/summary...")
        try:
            response = await client.get(f"{base_url}/summary")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Monitoring Summary:")
                print(f"  - Overall Status: {data['overall_status'].upper()}")
                print(f"  - Timestamp: {data['timestamp']}")
                print(f"  - System CPU: {data['system']['cpu_percent']}%")
                print(f"  - System Memory: {data['system']['memory_percent']}%")
                print(f"  - Services Checked: {len(data['services'])}")

                healthy = sum(1 for s in data['services'] if s['status'] == 'healthy')
                unhealthy = sum(1 for s in data['services'] if s['status'] == 'unhealthy')
                print(f"    - Healthy: {healthy}")
                print(f"    - Unhealthy: {unhealthy}")
            else:
                print(f"✗ Failed: HTTP {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Error: {e}")

        # Test 4: Logs
        print("\n[4] Testing /monitoring/logs...")
        try:
            response = await client.get(f"{base_url}/logs?limit=10")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Application Logs:")
                print(f"  - Retrieved {len(data)} log entries")
                for log in data[:3]:  # Show first 3
                    print(f"    [{log['level']}] {log['message']} (source: {log.get('source', 'N/A')})")
            else:
                print(f"✗ Failed: HTTP {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Error: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    print("Starting monitoring endpoints test...")
    print("Make sure the backend server is running on http://localhost:3000")
    print()

    try:
        asyncio.run(test_monitoring_endpoints())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
