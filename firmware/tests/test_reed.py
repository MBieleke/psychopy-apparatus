"""
Test script for reed sensor measurement functionality.

This script demonstrates how to use the reed sensor measurement features.
Run with: python firmware/tests/test_reed.py COM6

Replace COM6 with your actual serial port.
"""

import sys
import time
from psychopy.hardware import DeviceManager
from psychopy_apparatus.hardware.apparatus import Apparatus

def test_reed_measurement(port):
    """Test reed sensor measurement on apparatus."""
    
    print(f"Connecting to Apparatus on {port}...")
    
    # Create device in DeviceManager
    device_config = {
        'port': port,
        'baudrate': 115200,
        'debug': True
    }
    
    DeviceManager.addDevice(
        deviceName='apparatus1',
        deviceClass='psychopy_apparatus.hardware.apparatusDevice.ApparatusDevice',
        **device_config
    )
    
    # Create Apparatus interface
    apparatus = Apparatus('apparatus1')
    
    print("Device initialized successfully!")
    print("\n" + "="*60)
    print("REED SENSOR MEASUREMENT TEST")
    print("="*60)
    
    try:
        # Test 1: Monitor all holes at 100 Hz
        print("\nTest 1: Monitor all holes (0-20) at 100 Hz for 5 seconds")
        print("-" * 60)
        
        success = apparatus.startReedMeasurement(rate=100, holes='all')
        if not success:
            print("ERROR: Failed to start measurement")
            return
        
        print("Measurement started. Try plugging/unplugging holes!")
        print("The firmware only sends data when state changes occur.")
        print("Monitoring for 5 seconds...")
        
        start_time = time.time()
        last_event_count = 0
        
        while time.time() - start_time < 5.0:
            apparatus.updateReedMeasurement()
            time.sleep(0.01)  # 10ms frame time
            
            # Print new events
            if len(apparatus.reedTimes) > last_event_count:
                for i in range(last_event_count, len(apparatus.reedTimes)):
                    action_str = 'insert' if apparatus.reedActions[i] == 1 else 'remove'
                    print(f"  [{apparatus.reedTimes[i]:.3f}s] Hole {apparatus.reedHoles[i]}: {action_str}")
                last_event_count = len(apparatus.reedTimes)
        
        apparatus.stopReedMeasurement()
        
        print(f"\nMeasurement complete!")
        print(f"  Total events: {len(apparatus.reedTimes)}")
        print(f"\nSummary per hole:")
        for summary in apparatus.reedSummary:
            print(f"    Hole {summary['hole']}: {summary['insertions']} insertions, "
                  f"{summary['removals']} removals, {summary['duration']:.3f}s active")
        
        # Test 2: Monitor inner holes only
        print("\n\nTest 2: Monitor inner holes (0-7) at 50 Hz for 5 seconds")
        print("-" * 60)
        
        success = apparatus.startReedMeasurement(rate=50, holes='inner')
        if not success:
            print("ERROR: Failed to start measurement")
            return
        
        print("Measurement started. Monitoring inner holes only...")
        
        start_time = time.time()
        last_event_count = 0
        
        while time.time() - start_time < 5.0:
            apparatus.updateReedMeasurement()
            time.sleep(0.02)
            
            # Print new events
            if len(apparatus.reedTimes) > last_event_count:
                for i in range(last_event_count, len(apparatus.reedTimes)):
                    action_str = 'insert' if apparatus.reedActions[i] == 1 else 'remove'
                    print(f"  [{apparatus.reedTimes[i]:.3f}s] Hole {apparatus.reedHoles[i]}: {action_str}")
                last_event_count = len(apparatus.reedTimes)
        
        apparatus.stopReedMeasurement()
        
        print(f"\nMeasurement complete!")
        print(f"  Total events: {len(apparatus.reedTimes)}")
        print(f"\nSummary per hole:")
        for summary in apparatus.reedSummary:
            print(f"    Hole {summary['hole']}: {summary['insertions']} insertions, "
                  f"{summary['removals']} removals, {summary['duration']:.3f}s active")
        
        # Test 3: Monitor specific holes
        print("\n\nTest 3: Monitor holes [0, 5, 10] at 100 Hz for 5 seconds")
        print("-" * 60)
        
        success = apparatus.startReedMeasurement(rate=100, holes=[0, 5, 10])
        if not success:
            print("ERROR: Failed to start measurement")
            return
        
        print("Measurement started. Monitoring holes 0, 5, and 10 only...")
        
        start_time = time.time()
        last_event_count = 0
        
        while time.time() - start_time < 5.0:
            apparatus.updateReedMeasurement()
            time.sleep(0.01)
            
            # Print new events
            if len(apparatus.reedTimes) > last_event_count:
                for i in range(last_event_count, len(apparatus.reedTimes)):
                    action_str = 'insert' if apparatus.reedActions[i] == 1 else 'remove'
                    print(f"  [{apparatus.reedTimes[i]:.3f}s] Hole {apparatus.reedHoles[i]}: {action_str}")
                last_event_count = len(apparatus.reedTimes)
        
        apparatus.stopReedMeasurement()
        
        print(f"\nMeasurement complete!")
        print(f"  Total events: {len(apparatus.reedTimes)}")
        print(f"\nSummary per hole:")
        for summary in apparatus.reedSummary:
            print(f"    Hole {summary['hole']}: {summary['insertions']} insertions, "
                  f"{summary['removals']} removals, {summary['duration']:.3f}s active")
        
        # Data structure example
        print("\n" + "="*60)
        print("DATA STRUCTURE EXAMPLES")
        print("="*60)
        if len(apparatus.reedTimes) > 0:
            print(f"\nParallel list structure (easy for pandas/analysis):")
            print(f"  reedTimes:   {apparatus.reedTimes[:5]}..." if len(apparatus.reedTimes) > 5 else f"  reedTimes:   {apparatus.reedTimes}")
            print(f"  reedHoles:   {apparatus.reedHoles[:5]}..." if len(apparatus.reedHoles) > 5 else f"  reedHoles:   {apparatus.reedHoles}")
            print(f"  reedActions: {apparatus.reedActions[:5]}..." if len(apparatus.reedActions) > 5 else f"  reedActions: {apparatus.reedActions}")
            print(f"  (1=insert, 0=remove)")
            if len(apparatus.reedTimes) > 5:
                print(f"  ... and {len(apparatus.reedTimes) - 5} more events")
        else:
            print("\nNo events recorded.")
        
        if len(apparatus.reedSummary) > 0:
            print(f"\nSummary statistics (only active holes):")
            for summary in apparatus.reedSummary:
                print(f"  {summary}")
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        apparatus.stopReedMeasurement()
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        apparatus.stopReedMeasurement()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_reed.py <serial_port>")
        print("Example: python test_reed.py COM6")
        sys.exit(1)
    
    port = sys.argv[1]
    test_reed_measurement(port)
