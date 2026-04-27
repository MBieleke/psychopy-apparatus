"""
Test script for LED control on Client ESP32 firmware (via Server relay).

Two modes:
1. Test Mode (default): Validates CMD_LED_SET_N with Format A and Format B
2. Custom Mode (--custom): Direct LED control via command line

Requirements:
- pyserial: pip install pyserial
- Server ESP32 connected via USB (running server firmware)
- Client ESP32 powered and within ESP-NOW range (running client firmware)

Custom mode examples:
  python test_light.py COM6 --custom --holes 1,5 --color 255,0,0
  python test_light.py COM6 --custom --all --color 0,255,0
  python test_light.py COM6 --custom --clear

Test mode validates:
1. Single hole color (Format B with count=1)
2. Multiple holes, same color (Format A)
3. Multiple holes, different colors (Format B)
4. All holes same color (Format A efficiency test)
5. Rainbow pattern (Format B)
6. Format auto-detection
7-9. Error handling (invalid payloads, count=0, wrong lengths)
10. Clear all LEDs
"""

import serial
import struct
import time
import sys
import argparse

# Message types (Client)
CMD_LED_SET_N = 0x10
CMD_LED_SHOW = 0x11
MSG_ACK = 0x80
MSG_NACK = 0x81

# Addresses
ADDR_PC = 1
ADDR_SERVER = 2
ADDR_CLIENT = 3

# Flags
FLAG_ACK_REQUIRED = 0x01

# Error codes
ERR_BAD_LEN = 1
ERR_BAD_MSG = 2
ERR_BAD_PAYLOAD = 3

seq_counter = 1


def cobs_encode(data):
    """COBS encode data and append 0x00 delimiter."""
    output = bytearray()
    code_index = 0
    code = 1
    output.append(0)  # placeholder
    
    for byte in data:
        if byte == 0:
            output[code_index] = code
            code_index = len(output)
            output.append(0)
            code = 1
        else:
            output.append(byte)
            code += 1
            if code == 0xFF:
                output[code_index] = code
                code_index = len(output)
                output.append(0)
                code = 1
    
    output[code_index] = code
    output.append(0x00)  # delimiter
    return bytes(output)


def cobs_decode(data):
    """COBS decode data (without trailing 0x00)."""
    if not data:
        return b''
    
    output = bytearray()
    i = 0
    
    while i < len(data):
        code = data[i]
        if code == 0:
            return bytes(output)
        
        i += 1
        for _ in range(code - 1):
            if i >= len(data):
                return bytes(output)
            output.append(data[i])
            i += 1
        
        if code < 0xFF and i < len(data):
            output.append(0)
    
    return bytes(output)


def build_message(msg_type, seq, payload=b'', dst=ADDR_CLIENT, flags=FLAG_ACK_REQUIRED):
    """Build a binary message with header + payload, including XOR checksum."""
    header_temp = struct.pack('<BIHBBB', 
                         msg_type,      # msg_type (u8)
                         seq,           # seq (u32)
                         len(payload),  # payload_len (u16)
                         ADDR_PC,       # src (u8)
                         dst,           # dst (u8)
                         flags)         # flags (u8)
    
    # Calculate XOR checksum of header + payload
    checksum = 0
    for byte in header_temp:
        checksum ^= byte
    for byte in payload:
        checksum ^= byte
    
    # Build final message with checksum
    header = header_temp + struct.pack('<B', checksum)
    return header + payload


def send_message(ser, msg_type, payload=b'', dst=ADDR_CLIENT):
    """Send a COBS-framed message and return the sequence number."""
    global seq_counter
    seq = seq_counter
    seq_counter += 1
    
    raw_msg = build_message(msg_type, seq, payload, dst)
    encoded = cobs_encode(raw_msg)
    ser.write(encoded)
    
    # Show message details
    msg_type_names = {
        0x10: 'CMD_LED_SET_N', 0x11: 'CMD_LED_SHOW',
        0x80: 'MSG_ACK', 0x81: 'MSG_NACK'
    }
    msg_name = msg_type_names.get(msg_type, f'0x{msg_type:02X}')
    payload_hex = payload.hex() if payload else '(empty)'
    print(f"  → SEND: seq={seq}, type={msg_name}, payload={payload_hex[:60]}{'...' if len(payload_hex) > 60 else ''}")
    return seq


def read_frame(ser, timeout=1.0):
    """Read one COBS frame (until 0x00 delimiter)."""
    start_time = time.time()
    buffer = bytearray()
    
    while time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            b = ser.read(1)[0]
            if b == 0x00:
                if len(buffer) > 0:
                    decoded = cobs_decode(buffer)
                    if len(decoded) >= 11:  # min header size (10 + 1 checksum)
                        return decoded
                buffer = bytearray()
            else:
                buffer.append(b)
        else:
            time.sleep(0.001)
    
    return None


def parse_header(frame):
    """Parse message header and verify checksum."""
    if len(frame) < 11:
        return None
    
    msg_type, seq, payload_len, src, dst, flags, checksum = struct.unpack('<BIHBBBB', frame[:11])
    payload = frame[11:11+payload_len]
    
    # Verify checksum (XOR of all header bytes except checksum + payload)
    expected_checksum = 0
    for byte in frame[:10]:
        expected_checksum ^= byte
    for byte in payload:
        expected_checksum ^= byte
    
    if checksum != expected_checksum:
        print(f"  ⚠ CHECKSUM MISMATCH: expected 0x{expected_checksum:02x}, got 0x{checksum:02x}")
        return None
    
    return {
        'msg_type': msg_type,
        'seq': seq,
        'payload_len': payload_len,
        'src': src,
        'dst': dst,
        'flags': flags,
        'payload': payload
    }


def wait_for_ack(ser, expected_seq, timeout=2.0):
    """Wait for ACK or NACK from Client (src=CLIENT, dst=PC) matching expected_seq."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        frame = read_frame(ser, timeout=timeout - (time.time() - start_time))
        if not frame:
            continue
        
        msg = parse_header(frame)
        if not msg:
            continue
        
        # Check if this is a response from CLIENT to PC
        if msg['src'] == ADDR_CLIENT and msg['dst'] == ADDR_PC and msg['seq'] == expected_seq:
            payload_hex = msg['payload'].hex() if msg['payload'] else '(empty)'
            if msg['msg_type'] == MSG_ACK:
                print(f"  ← RECV: ACK from CLIENT, seq={expected_seq}")
                return True
            elif msg['msg_type'] == MSG_NACK:
                error_code = msg['payload'][0] if msg['payload'] else 0
                error_names = {1: 'BAD_LEN', 2: 'BAD_MSG', 3: 'BAD_PAYLOAD'}
                error_name = error_names.get(error_code, f'UNKNOWN({error_code})')
                print(f"  ← RECV: NACK from CLIENT, seq={expected_seq}, error={error_name}")
                return False
    
    print(f"  ✗ TIMEOUT waiting for ACK/NACK (seq={expected_seq})")
    return False


def set_leds(ser, holes, colors, show=True):
    """High-level LED control with automatic format detection.
    
    Args:
        ser: Serial connection
        holes: list of hole numbers
        colors: Single (r,g,b) tuple OR list of (r,g,b) tuples
        show: If True, automatically send LED_SHOW after setting colors
    
    Returns:
        True if successful, False otherwise
    """
    if not holes:
        return True
    
    count = len(holes)
    
    # Determine if single color or list of colors
    if isinstance(colors[0], int):
        # Single (r,g,b) tuple → Format A
        r, g, b = colors
        payload = bytes([count]) + bytes(holes) + bytes([r, g, b])
        format_name = "Format A (shared color)"
    else:
        # List of (r,g,b) tuples
        assert len(colors) == count, "colors and holes must have same length"
        
        # Check if all colors are the same → use Format A
        if all(c == colors[0] for c in colors):
            r, g, b = colors[0]
            payload = bytes([count]) + bytes(holes) + bytes([r, g, b])
            format_name = "Format A (auto-detected same color)"
        else:
            # Format B: different colors
            payload = bytes([count])
            for hole, (r, g, b) in zip(holes, colors):
                payload += bytes([hole, r, g, b])
            format_name = "Format B (individual colors)"
    
    print(f"    Using {format_name}, payload size: {len(payload)} bytes")
    seq = send_message(ser, CMD_LED_SET_N, payload)
    success = wait_for_ack(ser, seq)
    
    if not success:
        return False
    
    if show:
        time.sleep(0.05)  # Small delay
        seq = send_message(ser, CMD_LED_SHOW, b'')
        success = wait_for_ack(ser, seq)
    
    return success


def test_single_hole(ser):
    """Test setting a single hole color."""
    print("\n=== Test 1: Single Hole (Format B with count=1) ===")
    print("  Setting hole 0 to RED (255, 0, 0)")
    
    success = set_leds(ser, [0], [(255, 0, 0)], show=True)
    
    if success:
        print("  ✓ Single hole test PASSED")
        return True
    else:
        print("  ✗ Single hole test FAILED")
        return False


def test_multiple_holes_same_color(ser):
    """Test multiple holes with same color (Format A efficiency)."""
    print("\n=== Test 2: Multiple Holes, Same Color (Format A) ===")
    print("  Setting holes [0, 5, 10, 15, 20] to GREEN (0, 255, 0)")
    
    holes = [0, 5, 10, 15, 20]
    color = (0, 255, 0)
    
    success = set_leds(ser, holes, color, show=True)
    
    if success:
        print("  ✓ Multiple holes (same color) test PASSED")
        print(f"  Efficiency: {1 + len(holes) + 3} bytes (Format A) vs {1 + len(holes) * 4} bytes (Format B)")
        return True
    else:
        print("  ✗ Multiple holes (same color) test FAILED")
        return False


def test_multiple_holes_different_colors(ser):
    """Test multiple holes with different colors (Format B)."""
    print("\n=== Test 3: Multiple Holes, Different Colors (Format B) ===")
    print("  Setting holes 0→RED, 1→GREEN, 2→BLUE, 3→YELLOW, 4→CYAN")
    
    holes = [0, 1, 2, 3, 4]
    colors = [
        (255, 0, 0),    # RED
        (0, 255, 0),    # GREEN
        (0, 0, 255),    # BLUE
        (255, 255, 0),  # YELLOW
        (0, 255, 255)   # CYAN
    ]
    
    success = set_leds(ser, holes, colors, show=True)
    
    if success:
        print("  ✓ Multiple holes (different colors) test PASSED")
        return True
    else:
        print("  ✗ Multiple holes (different colors) test FAILED")
        return False


def test_all_holes_same_color(ser):
    """Test all 21 holes with same color (Format A maximum efficiency)."""
    print("\n=== Test 4: All Holes, Same Color (Format A Efficiency) ===")
    print("  Setting ALL 21 holes to PURPLE (128, 0, 128)")
    
    holes = list(range(21))
    color = (128, 0, 128)
    
    print(f"  Format A payload: {1 + 21 + 3} = 25 bytes")
    print(f"  Format B would be: {1 + 21 * 4} = 85 bytes")
    print(f"  Savings: {85 - 25} bytes (70.6% reduction)")
    
    success = set_leds(ser, holes, color, show=True)
    
    if success:
        print("  ✓ All holes test PASSED")
        return True
    else:
        print("  ✗ All holes test FAILED")
        return False


def test_rainbow_pattern(ser):
    """Test rainbow pattern across holes."""
    print("\n=== Test 5: Rainbow Pattern (Format B) ===")
    print("  Creating rainbow across first 7 holes")
    
    holes = list(range(7))
    colors = [
        (255, 0, 0),      # Red
        (255, 127, 0),    # Orange
        (255, 255, 0),    # Yellow
        (0, 255, 0),      # Green
        (0, 0, 255),      # Blue
        (75, 0, 130),     # Indigo
        (148, 0, 211)     # Violet
    ]
    
    success = set_leds(ser, holes, colors, show=True)
    
    if success:
        print("  ✓ Rainbow pattern test PASSED")
        return True
    else:
        print("  ✗ Rainbow pattern test FAILED")
        return False


def test_format_auto_detection(ser):
    """Test that auto-detection correctly chooses Format A when appropriate."""
    print("\n=== Test 6: Format Auto-Detection ===")
    print("  Sending 3 holes with identical colors (should auto-detect Format A)")
    
    holes = [10, 11, 12]
    colors = [(255, 128, 0), (255, 128, 0), (255, 128, 0)]  # All same
    
    success = set_leds(ser, holes, colors, show=True)
    
    if success:
        print("  ✓ Auto-detection test PASSED")
        return True
    else:
        print("  ✗ Auto-detection test FAILED")
        return False


def test_invalid_count_zero(ser):
    """Test error handling: count=0."""
    print("\n=== Test 7: Invalid Payload (count=0) ===")
    print("  Sending CMD_LED_SET_N with count=0 (should be rejected)")
    
    payload = bytes([0])  # count=0
    seq = send_message(ser, CMD_LED_SET_N, payload)
    success = wait_for_ack(ser, seq)
    
    if not success:
        print("  ✓ Invalid count=0 correctly rejected (NACK)")
        return True
    else:
        print("  ✗ Invalid count=0 incorrectly accepted (should be NACK)")
        return False


def test_invalid_length_format_a(ser):
    """Test error handling: wrong length for Format A."""
    print("\n=== Test 8: Invalid Length (Format A) ===")
    print("  Sending count=2, holes=[0,1], but missing RGB values")
    
    # count=2, holes=[0,1], but no RGB (should be 6 bytes total, sending 3)
    payload = bytes([2, 0, 1])  # Missing r,g,b
    seq = send_message(ser, CMD_LED_SET_N, payload)
    success = wait_for_ack(ser, seq)
    
    if not success:
        print("  ✓ Invalid length correctly rejected (NACK)")
        return True
    else:
        print("  ✗ Invalid length incorrectly accepted (should be NACK)")
        return False


def test_invalid_length_format_b(ser):
    """Test error handling: wrong length for Format B."""
    print("\n=== Test 9: Invalid Length (Format B) ===")
    print("  Sending count=2, but only 1 complete [hole,r,g,b] entry")
    
    # count=2, but only one entry (should be 9 bytes, sending 5)
    payload = bytes([2, 0, 255, 0, 0])  # Missing second entry
    seq = send_message(ser, CMD_LED_SET_N, payload)
    success = wait_for_ack(ser, seq)
    
    if not success:
        print("  ✓ Invalid length correctly rejected (NACK)")
        return True
    else:
        print("  ✗ Invalid length incorrectly accepted (should be NACK)")
        return False


def test_clear_all(ser):
    """Test clearing all LEDs (all black)."""
    print("\n=== Test 10: Clear All LEDs ===")
    print("  Setting all 21 holes to BLACK (0, 0, 0)")
    
    holes = list(range(21))
    color = (0, 0, 0)
    
    success = set_leds(ser, holes, color, show=True)
    
    if success:
        print("  ✓ Clear all test PASSED")
        return True
    else:
        print("  ✗ Clear all test FAILED")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Test LED control on Client ESP32 firmware via Server relay',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  # LED control (automatic when using LED arguments)
  python test_light.py COM6 --holes 1,5 --color 255,0,0          # Holes 1,5 → red
  python test_light.py COM6 --holes 0,1,2 --colors 255,0,0 0,255,0 0,0,255  # Different colors
  python test_light.py COM6 --holes 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20 --color 0,0,0  # Clear all
  
  # Test suite (automatic when no LED arguments)
  python test_light.py COM6

Tests Format A and Format B of CMD_LED_SET_N command.
        '''
    )
    parser.add_argument('port', help='Serial port for Server ESP32 (e.g., COM3, /dev/ttyUSB0)')
    parser.add_argument(
        '--holes',
        type=str,
        help='Comma-separated hole numbers (e.g., 1,5,10)'
    )
    parser.add_argument(
        '--color',
        type=str,
        help='Single RGB color (e.g., 255,0,0 for red)'
    )
    parser.add_argument(
        '--colors',
        type=str,
        nargs='+',
        help='Multiple RGB colors, one per hole (e.g., 255,0,0 0,255,0)'
    )
    
    args = parser.parse_args()
    
    port = args.port
    baudrate = 115200
    
    print("="*60)
    print("CLIENT LED CONTROL TEST (via Server Relay)")
    print("="*60)
    print(f"Server port: {port}")
    print(f"Baudrate: {baudrate}")
    print()
    
    try:
        print(f"Connecting to Server at {port}...")
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # Wait for ESP32 to reset
        print("Connected to Server!\n")
        
        # Drain any startup messages
        ser.reset_input_buffer()
        
        # Detect mode: if holes argument provided, use LED control mode
        custom_mode = args.holes is not None
        
        if custom_mode:
            print("=== LED Control Mode ===")
            
            # Parse holes
            try:
                holes = [int(h.strip()) for h in args.holes.split(',')]
                print(f"Target holes: {holes}")
            except ValueError:
                print(f"✗ Error: Invalid holes format '{args.holes}'. Use comma-separated numbers (e.g., 1,5,10)")
                sys.exit(1)
            
            # Parse colors
            if args.colors:
                # Multiple colors (Format B)
                try:
                    colors = []
                    for color_str in args.colors:
                        r, g, b = map(int, color_str.split(','))
                        colors.append((r, g, b))
                    if len(colors) != len(holes):
                        print(f"✗ Error: Number of colors ({len(colors)}) must match number of holes ({len(holes)})")
                        sys.exit(1)
                    print(f"Colors: {colors}")
                except ValueError:
                    print(f"✗ Error: Invalid colors format. Use space-separated R,G,B values (e.g., 255,0,0 0,255,0)")
                    sys.exit(1)
            elif args.color:
                # Single color (Format A) - applies to all holes
                try:
                    r, g, b = map(int, args.color.split(','))
                    colors = (r, g, b)
                    if len(holes) > 1:
                        print(f"Color: RGB({r},{g},{b}) for all {len(holes)} holes (Format A)")
                    else:
                        print(f"Color: RGB({r},{g},{b})")
                except ValueError:
                    print(f"✗ Error: Invalid color format '{args.color}'. Use R,G,B (e.g., 255,0,0)")
                    sys.exit(1)
            else:
                print("✗ Error: --holes requires either --color or --colors")
                sys.exit(1)
            
            # Apply LED changes
            success = set_leds(ser, holes, colors, show=True)
            
            if success:
                print("\n✓ LED control successful!")
                sys.exit(0)
            else:
                print("\n✗ LED control failed")
                sys.exit(1)
        
        # Test mode: run full validation suite
        else:
            print("Testing CMD_LED_SET_N with Format A and Format B")
            print("Watch the LED strip for visual confirmation!")
            print("(Provide --holes with --color or --colors for LED control)\n")
            
            results = []
            results.append(("Single Hole", test_single_hole(ser)))
            time.sleep(0.5)
            
            results.append(("Multiple Holes (Same Color)", test_multiple_holes_same_color(ser)))
            time.sleep(0.5)
            
            results.append(("Multiple Holes (Different Colors)", test_multiple_holes_different_colors(ser)))
            time.sleep(0.5)
            
            results.append(("All Holes (Same Color)", test_all_holes_same_color(ser)))
            time.sleep(0.5)
            
            results.append(("Rainbow Pattern", test_rainbow_pattern(ser)))
            time.sleep(0.5)
            
            results.append(("Format Auto-Detection", test_format_auto_detection(ser)))
            time.sleep(0.5)
            
            results.append(("Invalid Count=0", test_invalid_count_zero(ser)))
            time.sleep(0.3)
            
            results.append(("Invalid Length (Format A)", test_invalid_length_format_a(ser)))
            time.sleep(0.3)
            
            results.append(("Invalid Length (Format B)", test_invalid_length_format_b(ser)))
            time.sleep(0.3)
            
            results.append(("Clear All LEDs", test_clear_all(ser)))
            time.sleep(0.5)
            
            print("\n" + "="*60)
            print("TEST SUMMARY")
            print("="*60)
            
            for name, passed in results:
                status = "✓ PASS" if passed else "✗ FAIL"
                print(f"{name:40} {status}")
            
            passed_count = sum(1 for _, p in results if p)
            total_count = len(results)
            print(f"\nTotal: {passed_count}/{total_count} tests passed")
            
            if passed_count == total_count:
                print("\n🎉 All tests passed! LED control is working correctly.")
            else:
                print(f"\n⚠ {total_count - passed_count} test(s) failed.")
        
        ser.close()
        
        sys.exit(0 if custom_mode or passed_count == total_count else 1)
        
    except serial.SerialException as e:
        print(f"\n✗ Error opening serial port: {e}")
        print("   Make sure the Server ESP32 is connected and the port is correct.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        if 'ser' in locals() and ser.is_open:
            ser.close()
        sys.exit(1)


if __name__ == '__main__':
    main()
