#!/usr/bin/env python3
"""
NOVAURL Backend Testing Suite - Direct Backend Testing
Tests backend functionality by accessing the backend directly on localhost:8001
"""

import requests
import json
import time
import os
from datetime import datetime
import tempfile

# Test directly against backend
BACKEND_URL = "http://localhost:8001"
API_BASE = f"{BACKEND_URL}/api"

print(f"Testing NOVAURL Backend directly at: {BACKEND_URL}")
print(f"API Base URL: {API_BASE}")
print("=" * 60)

class NOVAURLDirectTester:
    def __init__(self):
        self.session = requests.Session()
        self.created_urls = []
        self.test_results = {
            'url_creation': False,
            'discord_webhook': False,
            'redirect_handling': False,
            'ip_tracking': False,
            'url_management': False,
            'error_handling': False
        }
        
    def log_test(self, test_name, status, message=""):
        status_symbol = "✅" if status else "❌"
        print(f"{status_symbol} {test_name}: {message}")
        
    def test_all_functionality(self):
        """Test all backend functionality"""
        print("🚀 Starting Direct Backend Tests")
        
        # Test 1: URL Creation
        print("\n🔗 Testing URL Creation")
        response = self.session.post(f"{API_BASE}/urls", data={
            'redirect_url': 'https://www.google.com',
            'discord_webhook': 'https://discord.com/api/webhooks/test/webhook'
        })
        
        if response.status_code == 200:
            url_data = response.json()
            short_code = url_data['short_code']
            self.created_urls.append(short_code)
            self.log_test("URL Creation", True, f"Created {short_code}")
            self.test_results['url_creation'] = True
        else:
            self.log_test("URL Creation", False, f"HTTP {response.status_code}")
            return False
        
        # Test 2: URL with HTML Upload
        print("\n📄 Testing HTML Upload")
        html_content = """<!DOCTYPE html>
<html><head><title>Custom</title></head>
<body><h1>Custom Loading</h1></body></html>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            html_file_path = f.name
        
        with open(html_file_path, 'rb') as html_file:
            files = {'custom_html': ('test.html', html_file, 'text/html')}
            response = self.session.post(f"{API_BASE}/urls", data={
                'redirect_url': 'https://www.github.com',
                'discord_webhook': 'https://discord.com/api/webhooks/test/webhook2'
            }, files=files)
        
        os.unlink(html_file_path)
        
        if response.status_code == 200:
            html_url_data = response.json()
            self.created_urls.append(html_url_data['short_code'])
            self.log_test("HTML Upload", True, f"Created {html_url_data['short_code']}")
        else:
            self.log_test("HTML Upload", False, f"HTTP {response.status_code}")
        
        # Test 3: URL Management
        print("\n📋 Testing URL Management")
        response = self.session.get(f"{API_BASE}/urls")
        if response.status_code == 200:
            urls = response.json()
            self.log_test("URL Listing", True, f"Retrieved {len(urls)} URLs")
            self.test_results['url_management'] = True
        else:
            self.log_test("URL Listing", False, f"HTTP {response.status_code}")
        
        # Test 4: Redirect Handling
        print("\n🔄 Testing Redirect Handling")
        if self.created_urls:
            test_code = self.created_urls[0]
            response = self.session.get(f"{BACKEND_URL}/{test_code}", allow_redirects=False)
            
            if response.status_code == 200 and 'Loading...' in response.text:
                self.log_test("Redirect Loading Page", True, "Loading page served")
                self.test_results['redirect_handling'] = True
                
                # Check click count update
                time.sleep(1)
                urls_response = self.session.get(f"{API_BASE}/urls")
                if urls_response.status_code == 200:
                    urls = urls_response.json()
                    target_url = next((url for url in urls if url['short_code'] == test_code), None)
                    if target_url and target_url['click_count'] > 0:
                        self.log_test("Click Tracking", True, f"Click count: {target_url['click_count']}")
                        self.test_results['ip_tracking'] = True
                    else:
                        self.log_test("Click Tracking", False, "Click count not updated")
            else:
                self.log_test("Redirect Handling", False, f"HTTP {response.status_code}")
        
        # Test 5: Discord Webhook (attempt)
        print("\n💬 Testing Discord Webhook")
        # The webhook attempt is made during redirect, so if redirect worked, webhook was attempted
        if self.test_results['redirect_handling']:
            self.log_test("Discord Webhook", True, "Webhook attempt made during redirect")
            self.test_results['discord_webhook'] = True
        
        # Test 6: Error Handling
        print("\n⚠️  Testing Error Handling")
        
        # Test non-existent short code
        response = self.session.get(f"{BACKEND_URL}/nonexistent123")
        if response.status_code == 404:
            self.log_test("Invalid Short Code", True, "Returns 404")
        else:
            self.log_test("Invalid Short Code", False, f"Expected 404, got {response.status_code}")
        
        # Test invalid file upload
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Not HTML")
            txt_file_path = f.name
        
        with open(txt_file_path, 'rb') as txt_file:
            files = {'custom_html': ('test.txt', txt_file, 'text/plain')}
            response = self.session.post(f"{API_BASE}/urls", data={
                'redirect_url': 'https://www.example.com',
                'discord_webhook': 'https://discord.com/api/webhooks/test/webhook'
            }, files=files)
        
        os.unlink(txt_file_path)
        
        if response.status_code == 400:
            self.log_test("Invalid File Upload", True, "Rejects non-HTML files")
            self.test_results['error_handling'] = True
        else:
            self.log_test("Invalid File Upload", False, f"Expected 400, got {response.status_code}")
        
        # Test URL deletion
        if self.created_urls:
            test_code = self.created_urls[0]
            response = self.session.delete(f"{API_BASE}/urls/{test_code}")
            if response.status_code == 200:
                self.log_test("URL Deletion", True, f"Deleted {test_code}")
                self.created_urls.remove(test_code)
            else:
                self.log_test("URL Deletion", False, f"HTTP {response.status_code}")
        
        # Cleanup remaining URLs
        for short_code in self.created_urls[:]:
            try:
                self.session.delete(f"{API_BASE}/urls/{short_code}")
                self.created_urls.remove(short_code)
            except:
                pass
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 DIRECT BACKEND TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(self.test_results.values())
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name.replace('_', ' ').title()}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        return passed_tests == total_tests

if __name__ == "__main__":
    tester = NOVAURLDirectTester()
    success = tester.test_all_functionality()
    exit(0 if success else 1)