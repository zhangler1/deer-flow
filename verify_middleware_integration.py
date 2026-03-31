#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Verification script for Middleware Integration

This script verifies that the middleware integration is working correctly.
"""

import sys


def print_header(text):
    """Print a formatted header"""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def test_config_loading():
    """Test summarization configuration loading"""
    print_header("Test 1: Configuration Loading")
    
    try:
        from src.config.loader import load_summarization_config
        from src.config.summarization_config import get_summarization_config
        
        # Load configuration
        load_summarization_config()
        config = get_summarization_config()
        
        # Verify configuration
        print(f"✅ Configuration loaded successfully!")
        print(f"   - Enabled: {config.enabled}")
        print(f"   - Model: {config.model_name or 'default'}")
        
        if config.trigger:
            if isinstance(config.trigger, list):
                print(f"   - Triggers: {len(config.trigger)} configured")
                for i, t in enumerate(config.trigger):
                    print(f"      {i+1}. {t.type}: {t.value}")
            else:
                print(f"   - Trigger: {config.trigger.type}: {config.trigger.value}")
        
        print(f"   - Keep: {config.keep.type}: {config.keep.value}")
        print(f"   - Trim tokens: {config.trim_tokens_to_summarize}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_middleware_import():
    """Test middleware module import"""
    print_header("Test 2: Middleware Module Import")
    
    try:
        from src.middlewares.researcher_agent import create_researcher_agent
        print("✅ Middleware module imported successfully!")
        print(f"   - Function: create_researcher_agent")
        return True
    except Exception as e:
        print(f"❌ Middleware import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_creation():
    """Test agent creation with middleware"""
    print_header("Test 3: Agent Creation")
    
    try:
        from src.middlewares.researcher_agent import create_researcher_agent
        from src.config.loader import load_summarization_config
        
        # Load configuration first
        load_summarization_config()
        
        # Create agent (with empty tools for testing)
        print("🤖 Creating researcher agent with middleware...")
        agent = create_researcher_agent(
            tools=[],
            model=None,
            enable_summarization=True,
        )
        
        print(f"✅ Agent created successfully!")
        print(f"   - Type: {type(agent).__name__}")
        
        return True
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_file_exists():
    """Test that conf.yaml contains SUMMARIZATION block"""
    print_header("Test 4: Configuration File")
    
    try:
        import os
        import yaml
        
        config_path = os.path.join(os.getcwd(), "conf.yaml")
        
        if not os.path.exists(config_path):
            print(f"❌ conf.yaml not found at {config_path}")
            return False
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if 'SUMMARIZATION' not in config:
            print(f"❌ SUMMARIZATION block not found in conf.yaml")
            return False
        
        summarization_config = config['SUMMARIZATION']
        
        print(f"✅ Configuration file verified!")
        print(f"   - Path: {config_path}")
        print(f"   - SUMMARIZATION block: Present")
        print(f"   - Enabled: {summarization_config.get('enabled', False)}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration file check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests"""
    print_header("DeerFlow 1.0 Middleware Integration Verification")
    
    print("This script verifies that the middleware integration is working correctly.\n")
    
    # Run tests
    tests = [
        ("Configuration File Check", test_config_file_exists),
        ("Configuration Loading", test_config_loading),
        ("Middleware Import", test_middleware_import),
        ("Agent Creation", test_agent_creation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
    
    # Print summary
    print_header("Verification Summary")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status}: {test_name}")
    
    print(f"\n  Total: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n  🎉 All tests passed! Middleware integration is working correctly.")
        print("\n  Next steps:")
        print("    1. Start the server: uv run python server.py")
        print("    2. Check logs for middleware activation")
        print("    3. Test with a long conversation")
        print("    4. Monitor token consumption")
        return 0
    else:
        print("\n  ⚠️  Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
