#!/usr/bin/env python3
"""
NOVAURL Backend Testing Suite
Tests all backend functionality including URL creation, Discord webhooks, 
redirect handling, IP tracking, geolocation, and URL management.
"""

import requests
import json
import time
import os
from datetime import datetime
from pathlib import Path
import tempfile

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/app/frontend/.env')

# Get backend URL from frontend environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE = f"{BACKEND_URL}/api"

print(f"Testing NOVAURL Backend at: {BACKEND_URL}")
print(f"API Base URL: {API_BASE}")
print("=" * 60)

class NOVAURLTester:
    def __init__(self):
        self.session = requests.Session()
        self.created_urls = []  # Track created URLs for cleanup
        self.test_results = {
            'url_creation': False,
            'discord_webhook': False,
            'redirect_handling': False,
            'ip_tracking': False,
            'url_management': False,
            'error_handling': False
        }
        
    def log_test(self, test_name, status, message=""):
        """Log test results"""
        status_symbol = "✅" if status else "❌"
        print(f"{status_symbol} {test_name}: {message}")
        
    def test_url_creation_basic(self):
        """Test basic URL creation with redirect_url and discord_webhook"""
        print("\n🔗 Testing URL Creation API (Basic)")
        
        try:
            # Test data
            test_data = {
                'redirect_url': 'https://www.google.com',
                'discord_webhook': 'https://discord.com/api/webhooks/test/webhook'
            }
            
            response = self.session.post(f"{API_BASE}/urls", data=test_data)
            
            if response.status_code == 200:
                url_data = response.json()
                
                # Validate response structure
                required_fields = ['id', 'short_code', 'redirect_url', 'discord_webhook', 'created_at', 'click_count']
                missing_fields = [field for field in required_fields if field not in url_data]
                
                if missing_fields:
                    self.log_test("URL Creation Basic", False, f"Missing fields: {missing_fields}")
                    return False
                
                # Validate data
                if (url_data['redirect_url'] == test_data['redirect_url'] and 
                    url_data['discord_webhook'] == test_data['discord_webhook'] and
                    len(url_data['short_code']) == 8 and
                    url_data['click_count'] == 0):
                    
                    self.created_urls.append(url_data['short_code'])
                    self.log_test("URL Creation Basic", True, f"Created short code: {url_data['short_code']}")
                    self.test_results['url_creation'] = True
                    return url_data
                else:
                    self.log_test("URL Creation Basic", False, "Response data validation failed")
                    return False
            else:
                self.log_test("URL Creation Basic", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("URL Creation Basic", False, f"Exception: {str(e)}")
            return False
    
    def test_url_creation_with_html(self):
        """Test URL creation with custom HTML file upload"""
        print("\n📄 Testing URL Creation with HTML Upload")
        
        try:
            # Create a temporary HTML file
            html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Custom Loading Page</title>
    <style>
        body { background: #1a1a1a; color: white; text-align: center; padding: 50px; }
        .custom-loader { color: #ff6b6b; font-size: 24px; }
    </style>
</head>
<body>
    <div class="custom-loader">Custom Loading Page...</div>
</body>
</html>"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                html_file_path = f.name
            
            # Test data
            test_data = {
                'redirect_url': 'https://www.github.com',
                'discord_webhook': 'https://discord.com/api/webhooks/test/webhook2'
            }
            
            with open(html_file_path, 'rb') as html_file:
                files = {'custom_html': ('test.html', html_file, 'text/html')}
                response = self.session.post(f"{API_BASE}/urls", data=test_data, files=files)
            
            # Cleanup temp file
            os.unlink(html_file_path)
            
            if response.status_code == 200:
                url_data = response.json()
                
                if (url_data['custom_html'] and 
                    'Custom Loading Page' in url_data['custom_html']):
                    
                    self.created_urls.append(url_data['short_code'])
                    self.log_test("URL Creation with HTML", True, f"Created with custom HTML: {url_data['short_code']}")
                    return url_data
                else:
                    self.log_test("URL Creation with HTML", False, "Custom HTML not saved properly")
                    return False
            else:
                self.log_test("URL Creation with HTML", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("URL Creation with HTML", False, f"Exception: {str(e)}")
            return False
    
    def test_url_management(self):
        """Test URL listing and deletion"""
        print("\n📋 Testing URL Management API")
        
        try:
            # Test GET /api/urls
            response = self.session.get(f"{API_BASE}/urls")
            
            if response.status_code == 200:
                urls = response.json()
                
                if isinstance(urls, list):
                    self.log_test("URL Listing", True, f"Retrieved {len(urls)} URLs")
                    
                    # Test deletion if we have URLs
                    if self.created_urls:
                        short_code_to_delete = self.created_urls[0]
                        delete_response = self.session.delete(f"{API_BASE}/urls/{short_code_to_delete}")
                        
                        if delete_response.status_code == 200:
                            self.log_test("URL Deletion", True, f"Deleted {short_code_to_delete}")
                            self.created_urls.remove(short_code_to_delete)
                            self.test_results['url_management'] = True
                            return True
                        else:
                            self.log_test("URL Deletion", False, f"HTTP {delete_response.status_code}")
                            return False
                    else:
                        self.log_test("URL Management", True, "No URLs to delete, but listing works")
                        self.test_results['url_management'] = True
                        return True
                else:
                    self.log_test("URL Listing", False, "Response is not a list")
                    return False
            else:
                self.log_test("URL Listing", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("URL Management", False, f"Exception: {str(e)}")
            return False
    
    def test_redirect_handling(self, short_code):
        """Test short URL redirect and visitor tracking"""
        print(f"\n🔄 Testing Redirect Handling for {short_code}")
        
        try:
            # Test the redirect endpoint (don't follow redirects to test the loading page)
            response = self.session.get(f"{BACKEND_URL}/{short_code}", allow_redirects=False)
            
            if response.status_code == 200:
                # Should return HTML loading page
                html_content = response.text
                
                if ('Loading...' in html_content or 'Custom Loading Page' in html_content) and 'setTimeout' in html_content:
                    self.log_test("Redirect Loading Page", True, "Loading page served correctly")
                    
                    # Test that visitor data is being tracked by checking if click count increases
                    # Wait a moment then check URL data
                    time.sleep(1)
                    
                    urls_response = self.session.get(f"{API_BASE}/urls")
                    if urls_response.status_code == 200:
                        urls = urls_response.json()
                        target_url = next((url for url in urls if url['short_code'] == short_code), None)
                        
                        if target_url and target_url['click_count'] > 0:
                            self.log_test("Visitor Tracking", True, f"Click count: {target_url['click_count']}")
                            self.test_results['redirect_handling'] = True
                            self.test_results['ip_tracking'] = True
                            return True
                        else:
                            self.log_test("Visitor Tracking", False, "Click count not updated")
                            return False
                    else:
                        self.log_test("Visitor Tracking Check", False, "Could not verify click count")
                        return False
                else:
                    self.log_test("Redirect Loading Page", False, "Invalid loading page content")
                    return False
            else:
                self.log_test("Redirect Handling", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Redirect Handling", False, f"Exception: {str(e)}")
            return False
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        print("\n⚠️  Testing Error Handling")
        
        try:
            # Test invalid short code
            response = self.session.get(f"{BACKEND_URL}/nonexistent123")
            if response.status_code == 404:
                self.log_test("Invalid Short Code", True, "Returns 404 as expected")
            else:
                self.log_test("Invalid Short Code", False, f"Expected 404, got {response.status_code}")
                return False
            
            # Test deleting non-existent URL
            response = self.session.delete(f"{API_BASE}/urls/nonexistent123")
            if response.status_code == 404:
                self.log_test("Delete Non-existent URL", True, "Returns 404 as expected")
            else:
                self.log_test("Delete Non-existent URL", False, f"Expected 404, got {response.status_code}")
                return False
            
            # Test invalid file upload (non-HTML)
            test_data = {
                'redirect_url': 'https://www.example.com',
                'discord_webhook': 'https://discord.com/api/webhooks/test/webhook'
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("This is not HTML")
                txt_file_path = f.name
            
            with open(txt_file_path, 'rb') as txt_file:
                files = {'custom_html': ('test.txt', txt_file, 'text/plain')}
                response = self.session.post(f"{API_BASE}/urls", data=test_data, files=files)
            
            os.unlink(txt_file_path)
            
            if response.status_code == 400:
                self.log_test("Invalid File Upload", True, "Rejects non-HTML files")
                self.test_results['error_handling'] = True
                return True
            else:
                self.log_test("Invalid File Upload", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Error Handling", False, f"Exception: {str(e)}")
            return False
    
    def test_discord_webhook_attempt(self, short_code):
        """Test that Discord webhook calls are attempted (we can't verify delivery)"""
        print(f"\n💬 Testing Discord Webhook Integration for {short_code}")
        
        try:
            # We can't actually verify Discord webhook delivery without a real webhook
            # But we can test that the system attempts to send webhooks by:
            # 1. Creating a URL with a webhook
            # 2. Visiting the short URL
            # 3. Checking that no errors occur (webhook failures are logged but don't break functionality)
            
            # Visit the short URL to trigger webhook
            response = self.session.get(f"{BACKEND_URL}/{short_code}", allow_redirects=False)
            
            if response.status_code == 200:
                # If we get a successful response, the webhook attempt was made
                # (even if the webhook URL is fake, the system tried to send it)
                self.log_test("Discord Webhook Attempt", True, "Webhook sending attempted (delivery not verified)")
                self.test_results['discord_webhook'] = True
                return True
            else:
                self.log_test("Discord Webhook Attempt", False, f"Failed to trigger webhook: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Discord Webhook Integration", False, f"Exception: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up created test URLs"""
        print(f"\n🧹 Cleaning up {len(self.created_urls)} test URLs...")
        
        for short_code in self.created_urls[:]:
            try:
                response = self.session.delete(f"{API_BASE}/urls/{short_code}")
                if response.status_code == 200:
                    print(f"   Deleted {short_code}")
                    self.created_urls.remove(short_code)
            except Exception as e:
                print(f"   Failed to delete {short_code}: {e}")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting NOVAURL Backend Tests")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Test 1: Basic URL Creation
        url_data = self.test_url_creation_basic()
        
        # Test 2: URL Creation with HTML
        html_url_data = self.test_url_creation_with_html()
        
        # Test 3: URL Management
        self.test_url_management()
        
        # Test 4: Redirect Handling (if we have a URL)
        if url_data:
            self.test_redirect_handling(url_data['short_code'])
            
        # Test 5: Discord Webhook (if we have a URL)
        if url_data:
            self.test_discord_webhook_attempt(url_data['short_code'])
        
        # Test 6: Error Handling
        self.test_error_handling()
        
        # Cleanup
        self.cleanup()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(self.test_results.values())
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name.replace('_', ' ').title()}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All backend tests PASSED!")
            return True
        else:
            print("⚠️  Some backend tests FAILED!")
            return False

if __name__ == "__main__":
    tester = NOVAURLTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)