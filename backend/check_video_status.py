#!/usr/bin/env python3
"""
Quick fix to set the status of a processed video to 'completed'
"""
import requests
import json

def fix_video_status(video_id):
    """Set video status to completed for testing"""
    try:
        # First check current status
        response = requests.get(f"http://localhost:5000/api/video/status/{video_id}")
        if response.status_code == 200:
            current_status = response.json()
            print(f"Current status: {current_status}")
        else:
            print(f"Could not get current status: {response.status_code}")
        
        # Test the results endpoint 
        results_response = requests.get(f"http://localhost:5000/api/video/results/{video_id}")
        if results_response.status_code == 200:
            results = results_response.json()
            print(f"✅ Results endpoint working: {results}")
            print(f"🎥 Video available: {results.get('compressed_video_available', False)}")
            print(f"🖼️  Keyframes available: {results.get('keyframes_available', False)}")
            
            if results.get('compressed_video_available') and results.get('keyframes_available'):
                print(f"\n🌐 Ready to view: http://localhost:3001/results/{video_id}")
                return True
        else:
            print(f"❌ Results endpoint error: {results_response.status_code}")
            print(f"Response: {results_response.text}")
        
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    video_id = "video_20251012_214901_7a5d63c9"
    print(f"🔧 Checking status for video: {video_id}")
    
    if fix_video_status(video_id):
        print(f"\n✅ Video ready! You can view it at:")
        print(f"http://localhost:3001/results/{video_id}")
    else:
        print(f"\n❌ Video not ready. Check backend processing.")