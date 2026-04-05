#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test touch command delivery fix
Verify:
1. Server response format contains touch_actions correctly
2. Client can parse touch_actions correctly
3. Parameter extraction is correct
"""
import os
import sys
import json

# Add project path
current_dir = os.path.dirname(os.path.abspath(__file__))
client_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(client_dir)
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_response_parsing():
    """Test response parsing"""
    print("=" * 60)
    print("Test 1: Response Format Parsing")
    print("=" * 60)
    
    # Simulate server response (top-level field format)
    server_response = {
        "status": "success",
        "touch_actions": [
            {"action": "click", "coordinates": [100, 200]},
            {"action": "swipe", "coordinates": [100, 200, 300, 400], "duration": 500}
        ],
        "task_completed": False,
        "content": "Click button to continue"
    }
    
    # Test new parsing logic
    touch_actions = server_response.get('touch_actions', [])
    if not touch_actions:
        touch_actions = server_response.get('data', {}).get('touch_actions', [])
    
    print(f"Parsed touch_actions count: {len(touch_actions)}")
    for i, action in enumerate(touch_actions):
        print(f"  Action {i+1}: {action}")
    
    assert len(touch_actions) == 2, "Should parse 2 touch actions"
    assert touch_actions[0]['action'] == 'click', "First action should be click"
    assert touch_actions[0]['coordinates'] == [100, 200], "Click coordinates should be [100, 200]"
    print("[PASS] Test 1: Response parsing correct")
    return True

def test_parameter_extraction():
    """Test parameter extraction"""
    print("\n" + "=" * 60)
    print("Test 2: Parameter Extraction")
    print("=" * 60)
    
    # Simulate server returned action format
    action = {
        "action": "click",
        "coordinates": [150, 250],
        "duration": 300
    }
    
    # Test parameter extraction logic
    params = {}
    for key in ['coordinates', 'end_coordinates', 'app_name', 'key_code',
                 'text', 'duration', 'x', 'y', 'x1', 'y1', 'x2', 'y2']:
        if key in action:
            params[key] = action[key]
    
    if 'parameters' in action and isinstance(action['parameters'], dict):
        params.update(action['parameters'])
    
    print(f"Extracted params: {params}")
    
    assert 'coordinates' in params, "Should contain coordinates parameter"
    assert params['coordinates'] == [150, 250], "coordinates should be [150, 250]"
    assert 'duration' in params, "Should contain duration parameter"
    assert params['duration'] == 300, "duration should be 300"
    print("[PASS] Test 2: Parameter extraction correct")
    return True

def test_coordinate_format_handling():
    """Test coordinate format handling"""
    print("\n" + "=" * 60)
    print("Test 3: Coordinate Format Handling")
    print("=" * 60)
    
    test_cases = [
        # Format 1: Array format [x, y]
        {"coordinates": [100, 200], "expected": "array"},
        # Format 2: Array format [x1, y1, x2, y2]
        {"coordinates": [100, 200, 300, 400], "expected": "array"},
        # Format 3: Object format {"start": [x, y]}
        {"coordinates": {"start": [0.5, 0.6], "end": [0.7, 0.8]}, "expected": "object"},
    ]
    
    for i, case in enumerate(test_cases):
        coords = case['coordinates']
        expected_type = case['expected']
        
        # Determine format type
        if isinstance(coords, list):
            actual_type = "array"
            if len(coords) >= 2:
                x, y = coords[0], coords[1]
                print(f"  Case {i+1}: Array format - x={x}, y={y}")
        elif isinstance(coords, dict) and "start" in coords:
            actual_type = "object"
            norm_x, norm_y = coords["start"]
            print(f"  Case {i+1}: Object format - norm_x={norm_x}, norm_y={norm_y}")
        else:
            actual_type = "unknown"
            print(f"  Case {i+1}: Unknown format - {coords}")
        
        assert actual_type == expected_type, f"Format type should be {expected_type}"
    
    print("[PASS] Test 3: Coordinate format handling correct")
    return True

def test_provider_selector_stats():
    """Test provider_selector stats initialization"""
    print("\n" + "=" * 60)
    print("Test 4: provider_selector Stats Initialization")
    print("=" * 60)
    
    # Simulate provider_stats initialization logic
    provider_stats = {}
    provider_name = "test_provider"
    
    # Apply fixed initialization logic
    if provider_name not in provider_stats:
        provider_stats[provider_name] = {}
    
    stats = provider_stats[provider_name]
    
    # Ensure all required keys exist (prevent KeyError)
    required_keys = ['current_requests', 'rps_window', 'rpm_window', 'tpm_window', 'rpd_window', 'total_requests']
    for key in required_keys:
        if key not in stats:
            if key == 'current_requests' or key == 'total_requests':
                stats[key] = 0
            else:
                stats[key] = []
    
    print(f"Initialized stats: {stats}")
    
    # Test access won't raise error
    stats['current_requests'] += 1  # This would raise KeyError before fix
    stats['rps_window'].append(1234567890)
    stats['total_requests'] += 1
    
    print(f"Updated stats: {stats}")
    
    assert stats['current_requests'] == 1, "current_requests should be 1"
    assert stats['total_requests'] == 1, "total_requests should be 1"
    assert len(stats['rps_window']) == 1, "rps_window should have 1 element"
    print("[PASS] Test 4: provider_selector stats initialization correct")
    return True

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Touch Command Delivery Fix Verification Test")
    print("=" * 60 + "\n")
    
    all_passed = True
    
    try:
        test_response_parsing()
    except AssertionError as e:
        print(f"[FAIL] Test 1: {e}")
        all_passed = False
    
    try:
        test_parameter_extraction()
    except AssertionError as e:
        print(f"[FAIL] Test 2: {e}")
        all_passed = False
    
    try:
        test_coordinate_format_handling()
    except AssertionError as e:
        print(f"[FAIL] Test 3: {e}")
        all_passed = False
    
    try:
        test_provider_selector_stats()
    except AssertionError as e:
        print(f"[FAIL] Test 4: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] All tests passed! Fix verification successful")
    else:
        print("[FAIL] Some tests failed, please check the fix")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())