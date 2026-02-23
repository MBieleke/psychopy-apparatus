"""
Test script for handgrip force measurement functionality.

This script demonstrates how to use the force measurement features.
Run with: python firmware/tests/test_force.py COM6

Replace COM6 with your actual serial port.
"""

import sys
import time
from psychopy.hardware import DeviceManager
from psychopy_apparatus.hardware.apparatus import Apparatus

def test_force_measurement(port):
    """Test force measurement on handgrip dynamometer."""
    
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
    print("FORCE MEASUREMENT TEST")
    print("="*60)
    
    try:
        # Test 1: Measure white dynamometer at 100 Hz
        print("\nTest 1: White dynamometer at 100 Hz for 3 seconds")
        print("-" * 60)
        
        success = apparatus.startForceMeasurement(rate=100, device='white')
        if not success:
            print("ERROR: Failed to start measurement")
            return
        
        print("Measurement started. Squeeze the white dynamometer!")
        print("Collecting data for 3 seconds...")
        
        start_time = time.time()
        while time.time() - start_time < 3.0:
            apparatus.updateForceMeasurement()
            time.sleep(0.01)  # 10ms frame time
            
            # Print current force every 0.5 seconds
            if int((time.time() - start_time) * 2) % 1 == 0:
                print(f"  Current: {apparatus.whiteForce}N | Max: {apparatus.maxWhiteForce}N | Samples: {len(apparatus.responses)}")
                time.sleep(0.01)  # Avoid duplicate prints
        
        apparatus.stopForceMeasurement()
        
        print(f"\nMeasurement complete!")
        print(f"  Total samples: {len(apparatus.responses)}")
        print(f"  Max white force: {apparatus.maxWhiteForce}N")
        print(f"  Sample rate: {len(apparatus.responses)/3.0:.1f} Hz")
        print(f"\nData structure (human-readable):")
        print(f"  whiteForceValues: {apparatus.whiteForceValues[:5]}... ({len(apparatus.whiteForceValues)} values)")
        print(f"  whiteForceTimestamps: {[f'{t:.3f}' for t in apparatus.whiteForceTimestamps[:5]]}... ({len(apparatus.whiteForceTimestamps)} timestamps)")

        
        # Test 2: Measure blue dynamometer at 50 Hz
        print("\n\nTest 2: Blue dynamometer at 50 Hz for 2 seconds")
        print("-" * 60)
        
        success = apparatus.startForceMeasurement(rate=50, device='blue')
        if not success:
            print("ERROR: Failed to start measurement")
            return
        
        print("Measurement started. Squeeze the blue dynamometer!")
        print("Collecting data for 2 seconds...")
        
        start_time = time.time()
        while time.time() - start_time < 2.0:
            apparatus.updateForceMeasurement()
            time.sleep(0.01)
            
            if int((time.time() - start_time) * 2) % 1 == 0:
                print(f"  Current: {apparatus.blueForce}N | Max: {apparatus.maxBlueForce}N | Samples: {len(apparatus.responses)}")
                time.sleep(0.01)
        
        apparatus.stopForceMeasurement()
        
        print(f"\nMeasurement complete!")
        print(f"  Total samples: {len(apparatus.responses)}")
        print(f"  Max blue force: {apparatus.maxBlueForce}N")
        print(f"  Sample rate: {len(apparatus.responses)/2.0:.1f} Hz")
        print(f"\nData structure (human-readable):")
        print(f"  blueForceValues: {apparatus.blueForceValues[:5]}... ({len(apparatus.blueForceValues)} values)")
        print(f"  blueForceTimestamps: {[f'{t:.3f}' for t in apparatus.blueForceTimestamps[:5]]}... ({len(apparatus.blueForceTimestamps)} timestamps)")
        
        # Test 3: Measure both dynamometers at 200 Hz
        print("\n\nTest 3: Both dynamometers at 200 Hz for 2 seconds")
        print("-" * 60)
        
        success = apparatus.startForceMeasurement(rate=200, device='both')
        if not success:
            print("ERROR: Failed to start measurement")
            return
        
        print("Measurement started. Squeeze both dynamometers!")
        print("Collecting data for 2 seconds...")
        
        start_time = time.time()
        while time.time() - start_time < 2.0:
            apparatus.updateForceMeasurement()
            time.sleep(0.005)
            
            if int((time.time() - start_time) * 2) % 1 == 0:
                print(f"  White: {apparatus.whiteForce}N (max {apparatus.maxWhiteForce}N) | "
                      f"Blue: {apparatus.blueForce}N (max {apparatus.maxBlueForce}N) | "
                      f"Samples: {len(apparatus.responses)}")
                time.sleep(0.01)
        
        apparatus.stopForceMeasurement()
        
        print(f"\nMeasurement complete!")
        print(f"  Total samples: {len(apparatus.responses)}")
        print(f"  Max white force: {apparatus.maxWhiteForce}N")
        print(f"  Max blue force: {apparatus.maxBlueForce}N")
        print(f"  Sample rate: {len(apparatus.responses)/2.0:.1f} Hz")
        print(f"\nData structure (human-readable):")
        print(f"  whiteForceValues: {apparatus.whiteForceValues[:5]}... ({len(apparatus.whiteForceValues)} values)")
        print(f"  blueForceValues: {apparatus.blueForceValues[:5]}... ({len(apparatus.blueForceValues)} values)")
        print(f"  Total data points: {len(apparatus.whiteForceValues) + len(apparatus.blueForceValues)}")
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        apparatus.stopForceMeasurement()
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        apparatus.stopForceMeasurement()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_force.py <serial_port>")
        print("Example: python test_force.py COM6")
        sys.exit(1)
    
    port = sys.argv[1]
    test_force_measurement(port)
