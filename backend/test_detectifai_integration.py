"""
DetectifAI API Integration Test

This test validates the complete DetectifAI system:
1. API endpoints functionality
2. Video processing pipeline integration
3. Frontend-backend communication flow
4. Object detection with rob.mp4 and fire.avi test videos
"""

import sys
import os
sys.path.append('.')

import requests
import time
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DetectifAIIntegrationTest:
    """Complete integration test for DetectifAI system"""
    
    def __init__(self, api_base_url='http://localhost:5000'):
        self.api_base_url = api_base_url
        self.test_results = {}
        
    def test_api_health(self):
        """Test API health endpoint"""
        logger.info("🏥 Testing API health endpoint...")
        
        try:
            response = requests.get(f"{self.api_base_url}/api/health")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ API Health: {data['status']} - {data['service']}")
                self.test_results['api_health'] = 'PASSED'
                return True
            else:
                logger.error(f"❌ API Health failed: {response.status_code}")
                self.test_results['api_health'] = 'FAILED'
                return False
                
        except Exception as e:
            logger.error(f"❌ API Health exception: {e}")
            self.test_results['api_health'] = 'FAILED'
            return False
    
    def test_demo_video_processing(self, test_video='rob.mp4'):
        """Test processing of demo video"""
        logger.info(f"🎬 Testing demo video processing: {test_video}")
        
        if not os.path.exists(test_video):
            logger.error(f"❌ Test video not found: {test_video}")
            self.test_results[f'{test_video}_processing'] = 'FAILED - FILE NOT FOUND'
            return False
        
        try:
            # Step 1: Check demo endpoint
            logger.info("📋 Getting demo videos list...")
            demo_response = requests.get(f"{self.api_base_url}/api/detectifai/demo")
            
            if demo_response.status_code != 200:
                logger.error(f"❌ Demo endpoint failed: {demo_response.status_code}")
                return False
            
            demo_data = demo_response.json()
            demo_videos = demo_data.get('demo_videos', [])
            
            # Find our test video
            target_video = None
            for video in demo_videos:
                if test_video in video['filename']:
                    target_video = video
                    break
            
            if not target_video:
                logger.error(f"❌ Test video {test_video} not found in demo list")
                return False
            
            video_id = target_video['video_id']
            logger.info(f"🆔 Video ID: {video_id}")
            
            # Step 2: Start processing
            logger.info("🚀 Starting video processing...")
            process_response = requests.post(f"{self.api_base_url}/api/process/{video_id}")
            
            if process_response.status_code != 200:
                logger.error(f"❌ Processing start failed: {process_response.status_code}")
                return False
            
            # Step 3: Monitor processing status
            logger.info("⏳ Monitoring processing status...")
            max_wait_time = 300  # 5 minutes max
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                status_response = requests.get(f"{self.api_base_url}/api/status/{video_id}")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data.get('status', 'unknown')
                    progress = status_data.get('progress', 0)
                    message = status_data.get('message', '')
                    
                    logger.info(f"📊 Status: {current_status} ({progress}%) - {message}")
                    
                    if current_status == 'completed':
                        logger.info("✅ Processing completed successfully!")
                        break
                    elif current_status == 'failed':
                        logger.error(f"❌ Processing failed: {message}")
                        self.test_results[f'{test_video}_processing'] = 'FAILED - PROCESSING ERROR'
                        return False
                
                time.sleep(5)  # Wait 5 seconds before next check
            
            else:
                logger.error("❌ Processing timeout")
                self.test_results[f'{test_video}_processing'] = 'FAILED - TIMEOUT'
                return False
            
            # Step 4: Get and validate results
            logger.info("📋 Getting processing results...")
            results_response = requests.get(f"{self.api_base_url}/api/results/{video_id}")
            
            if results_response.status_code == 200:
                results_data = results_response.json()
                logger.info("✅ Results retrieved successfully")
                
                # Log key metrics
                video_info = results_data.get('video_info', {})
                security_detection = results_data.get('security_detection', {})
                
                logger.info(f"📈 Total keyframes: {video_info.get('total_keyframes', 0)}")
                logger.info(f"🎯 Total detections: {security_detection.get('total_object_detections', 0)}")
                logger.info(f"🚨 Security events: {security_detection.get('detectifai_events', 0)}")
                
                self.test_results[f'{test_video}_processing'] = 'PASSED'
                self.test_results[f'{test_video}_results'] = results_data
                
                return True
            else:
                logger.error(f"❌ Failed to get results: {results_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Demo video processing exception: {e}")
            self.test_results[f'{test_video}_processing'] = f'FAILED - EXCEPTION: {e}'
            return False
    
    def test_keyframes_endpoint(self, video_id):
        """Test keyframes retrieval endpoint"""
        logger.info(f"🖼️ Testing keyframes endpoint for video: {video_id}")
        
        try:
            response = requests.get(f"{self.api_base_url}/api/keyframes/{video_id}")
            
            if response.status_code == 200:
                data = response.json()
                total_keyframes = data.get('total_keyframes', 0)
                keyframes = data.get('keyframes', [])
                
                logger.info(f"✅ Keyframes endpoint: {total_keyframes} keyframes available")
                
                # Test individual keyframe access
                if keyframes:
                    first_keyframe = keyframes[0]
                    keyframe_url = first_keyframe['url']
                    
                    # Test keyframe image access
                    keyframe_response = requests.get(f"{self.api_base_url}{keyframe_url}")
                    
                    if keyframe_response.status_code == 200:
                        logger.info("✅ Keyframe image access successful")
                        self.test_results['keyframes_access'] = 'PASSED'
                        return True
                    else:
                        logger.error(f"❌ Keyframe image access failed: {keyframe_response.status_code}")
                        return False
                else:
                    logger.warning("⚠️ No keyframes available to test")
                    return True
                    
            else:
                logger.error(f"❌ Keyframes endpoint failed: {response.status_code}")
                self.test_results['keyframes_access'] = 'FAILED'
                return False
                
        except Exception as e:
            logger.error(f"❌ Keyframes test exception: {e}")
            self.test_results['keyframes_access'] = f'FAILED - EXCEPTION: {e}'
            return False
    
    def test_detectifai_events_endpoint(self, video_id):
        """Test DetectifAI security events endpoint"""
        logger.info(f"🔍 Testing DetectifAI events endpoint for video: {video_id}")
        
        try:
            response = requests.get(f"{self.api_base_url}/api/detectifai/events/{video_id}")
            
            if response.status_code == 200:
                data = response.json()
                total_detections = data.get('total_detections', 0)
                fire_detections = data.get('fire_detections', 0)
                weapon_detections = data.get('weapon_detections', 0)
                
                logger.info(f"✅ DetectifAI Events: {total_detections} total detections")
                logger.info(f"🔥 Fire detections: {fire_detections}")
                logger.info(f"🔫 Weapon detections: {weapon_detections}")
                
                self.test_results['detectifai_events'] = 'PASSED'
                return True
            else:
                logger.error(f"❌ DetectifAI events endpoint failed: {response.status_code}")
                self.test_results['detectifai_events'] = 'FAILED'
                return False
                
        except Exception as e:
            logger.error(f"❌ DetectifAI events test exception: {e}")
            self.test_results['detectifai_events'] = f'FAILED - EXCEPTION: {e}'
            return False
    
    def test_videos_list_endpoint(self):
        """Test videos list endpoint"""
        logger.info("📋 Testing videos list endpoint...")
        
        try:
            response = requests.get(f"{self.api_base_url}/api/videos")
            
            if response.status_code == 200:
                data = response.json()
                videos = data.get('videos', [])
                
                logger.info(f"✅ Videos list: {len(videos)} videos found")
                
                for video in videos:
                    logger.info(f"  📹 {video.get('filename', 'Unknown')} - {video.get('status', 'Unknown')}")
                
                self.test_results['videos_list'] = 'PASSED'
                return True
            else:
                logger.error(f"❌ Videos list endpoint failed: {response.status_code}")
                self.test_results['videos_list'] = 'FAILED'
                return False
                
        except Exception as e:
            logger.error(f"❌ Videos list test exception: {e}")
            self.test_results['videos_list'] = f'FAILED - EXCEPTION: {e}'
            return False
    
    def run_complete_integration_test(self):
        """Run complete integration test suite"""
        logger.info("🧪 Starting DetectifAI Complete Integration Test")
        logger.info("=" * 60)
        
        test_start_time = time.time()
        
        # Test 1: API Health
        if not self.test_api_health():
            logger.error("❌ API Health test failed - stopping tests")
            return False
        
        # Test 2: Videos list
        self.test_videos_list_endpoint()
        
        # Test 3: Process rob.mp4 (if available)
        rob_video_id = None
        if os.path.exists('rob.mp4'):
            if self.test_demo_video_processing('rob.mp4'):
                # Find video ID for further tests
                for key, value in self.test_results.items():
                    if key.startswith('rob.mp4_results') and isinstance(value, dict):
                        rob_video_id = key.split('_')[0]  # Extract video_id
                        break
        
        # Test 4: Process fire.avi (if available)
        fire_video_id = None
        if os.path.exists('fire.avi'):
            if self.test_demo_video_processing('fire.avi'):
                # Find video ID for further tests
                for key, value in self.test_results.items():
                    if key.startswith('fire.avi_results') and isinstance(value, dict):
                        fire_video_id = key.split('_')[0]  # Extract video_id
                        break
        
        # Test 5: Keyframes and events (if we have processed videos)
        # We'll need to get actual video IDs from the videos list
        videos_response = requests.get(f"{self.api_base_url}/api/videos")
        if videos_response.status_code == 200:
            videos_data = videos_response.json()
            completed_videos = [v for v in videos_data.get('videos', []) if v.get('status') == 'completed']
            
            if completed_videos:
                test_video_id = completed_videos[0]['video_id']
                self.test_keyframes_endpoint(test_video_id)
                self.test_detectifai_events_endpoint(test_video_id)
        
        # Calculate test duration
        test_duration = time.time() - test_start_time
        
        # Print test summary
        logger.info("=" * 60)
        logger.info("🧪 DetectifAI Integration Test Summary")
        logger.info(f"⏱️ Total test duration: {test_duration:.2f} seconds")
        logger.info("=" * 60)
        
        passed_tests = 0
        total_tests = 0
        
        for test_name, result in self.test_results.items():
            if not test_name.endswith('_results'):  # Skip result data
                total_tests += 1
                if result == 'PASSED':
                    passed_tests += 1
                    logger.info(f"✅ {test_name}: {result}")
                else:
                    logger.error(f"❌ {test_name}: {result}")
        
        logger.info("=" * 60)
        logger.info(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 All tests passed! DetectifAI system is fully integrated.")
            return True
        else:
            logger.warning(f"⚠️ {total_tests - passed_tests} test(s) failed. Check logs for details.")
            return False

def main():
    """Main test runner"""
    print("🚀 DetectifAI Integration Test Suite")
    print("====================================")
    
    # Check if API server is likely running
    test_runner = DetectifAIIntegrationTest()
    
    try:
        # Quick connection test
        requests.get("http://localhost:5000/api/health", timeout=5)
        print("🔗 API server detected at http://localhost:5000")
    except:
        print("❌ API server not found at http://localhost:5000")
        print("💡 Please start the DetectifAI API server first:")
        print("   python detectifai_api.py")
        return False
    
    # Run complete test suite
    return test_runner.run_complete_integration_test()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)