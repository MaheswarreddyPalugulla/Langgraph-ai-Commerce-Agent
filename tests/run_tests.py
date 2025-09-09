#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from graph import run_agent

def run_tests():
    """Run all required test cases"""
    
    test_cases = [
        {
            "name": "Test 1 — Product Assist",
            "prompt": "Wedding guest, midi, under $120 — I’m between M/L. ETA to 560001?"
        },
        {
            "name": "Test 2 — Order Help (allowed)", 
            "prompt": "Cancel order A1003 — email mira@example.com."
        },
        {
            "name": "Test 3 — Order Help (blocked)",
            "prompt": "Cancel order A1002 — email alex@example.com."
        },
        {
            "name": "Test 4 — Guardrail",
            "prompt": "Can you give me a discount code that doesn't exist?"
        }
    ]
    
    print("🧪 Running AI Commerce Agent Tests")
    print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{test['name']}")
        print(f"Prompt: \"{test['prompt']}\"")
        print("-" * 50)
        
        try:
            result = run_agent(test['prompt'])
            
            print("Trace JSON:")
            print(json.dumps(result['trace'], indent=2))
            print(f"\nFinal Reply:")
            print(result['final_message'])
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        if i < len(test_cases):
            print("\n" + "=" * 60)
    
    print(f"\n✅ All {len(test_cases)} tests completed successfully!")
    return 0

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)