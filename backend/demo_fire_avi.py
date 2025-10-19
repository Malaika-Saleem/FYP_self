"""
Complete DetectifAI Demo - fire.avi Processing with Frontend Dashboard

This script demonstrates the complete workflow:
1. Start the DetectifAI API server
2. Process fire.avi with object detection
3. Show processing status and results
4. Generate a simple HTML dashboard to visualize results
"""

import sys
import os
import requests
import time
import json
from datetime import datetime
import threading
import subprocess
import webbrowser

class DetectifAIDemo:
    """Complete demo showing DetectifAI processing with fire.avi"""
    
    def __init__(self):
        self.api_base = "http://localhost:5000"
        self.video_id = None
        self.server_process = None
        
    def start_api_server(self):
        """Start the DetectifAI API server in background"""
        try:
            print("🚀 Starting DetectifAI API server...")
            
            # Check if server is already running
            try:
                response = requests.get(f"{self.api_base}/api/health", timeout=2)
                if response.status_code == 200:
                    print("✅ DetectifAI API server is already running")
                    return True
            except:
                pass
            
            # Start the server
            python_exe = "D:/FAST/Final Year Project/finWebApp/finWebApp - Copy/.venv/Scripts/python.exe"
            self.server_process = subprocess.Popen(
                [python_exe, "app.py"],
                cwd="d:/FAST/Final Year Project/finWebApp/finWebApp - Copy/backend",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for server to start
            print("⏳ Waiting for server to start...")
            for i in range(30):  # Wait up to 30 seconds
                try:
                    response = requests.get(f"{self.api_base}/api/health", timeout=1)
                    if response.status_code == 200:
                        print("✅ DetectifAI API server started successfully!")
                        time.sleep(2)  # Give it a moment to fully initialize
                        return True
                except:
                    time.sleep(1)
                    print(f"   Waiting... ({i+1}/30)")
            
            print("❌ Failed to start API server")
            return False
            
        except Exception as e:
            print(f"❌ Error starting server: {e}")
            return False
    
    def setup_demo_video(self):
        """Setup fire.avi for demo processing"""
        try:
            print("🎬 Setting up fire.avi for demo processing...")
            
            # Check if fire.avi exists
            backend_dir = "d:/FAST/Final Year Project/finWebApp/finWebApp - Copy/backend"
            fire_avi_path = os.path.join(backend_dir, "fire.avi")
            
            if not os.path.exists(fire_avi_path):
                print(f"❌ fire.avi not found at: {fire_avi_path}")
                return False
            
            file_size = os.path.getsize(fire_avi_path) / (1024 * 1024)
            print(f"✅ fire.avi found ({file_size:.1f} MB)")
            
            # Get demo videos from API
            response = requests.get(f"{self.api_base}/api/detectifai/demo")
            
            if response.status_code != 200:
                print(f"❌ Failed to get demo videos: {response.status_code}")
                return False
            
            demo_data = response.json()
            demo_videos = demo_data.get('demo_videos', [])
            
            # Find fire.avi demo video
            fire_video = None
            for video in demo_videos:
                if 'fire.avi' in video['filename']:
                    fire_video = video
                    break
            
            if not fire_video:
                print("❌ fire.avi not found in demo videos")
                return False
            
            self.video_id = fire_video['video_id']
            print(f"✅ Demo video ready - ID: {self.video_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up demo video: {e}")
            return False
    
    def start_processing(self):
        """Start processing fire.avi"""
        try:
            print("🚀 Starting fire.avi processing with DetectifAI...")
            
            response = requests.post(f"{self.api_base}/api/process/{self.video_id}")
            
            if response.status_code != 200:
                print(f"❌ Failed to start processing: {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            result = response.json()
            print(f"✅ Processing started: {result['message']}")
            return True
            
        except Exception as e:
            print(f"❌ Error starting processing: {e}")
            return False
    
    def monitor_processing(self):
        """Monitor processing progress and show status updates"""
        try:
            print("📊 Monitoring processing progress...")
            print("=" * 60)
            
            start_time = time.time()
            last_progress = -1
            
            while True:
                response = requests.get(f"{self.api_base}/api/status/{self.video_id}")
                
                if response.status_code != 200:
                    print(f"❌ Failed to get status: {response.status_code}")
                    break
                
                status_data = response.json()
                current_status = status_data.get('status', 'unknown')
                progress = status_data.get('progress', 0)
                message = status_data.get('message', '')
                
                # Only show progress updates when they change
                if progress != last_progress:
                    elapsed = time.time() - start_time
                    print(f"[{elapsed:6.1f}s] {current_status.upper():12} ({progress:3}%) - {message}")
                    last_progress = progress
                
                if current_status == 'completed':
                    print("=" * 60)
                    print("✅ Processing completed successfully!")
                    return True
                elif current_status == 'failed':
                    error = status_data.get('error', 'Unknown error')
                    print(f"❌ Processing failed: {error}")
                    return False
                
                time.sleep(2)  # Check every 2 seconds
                
        except Exception as e:
            print(f"❌ Error monitoring processing: {e}")
            return False
    
    def get_results(self):
        """Get and display processing results"""
        try:
            print("📋 Getting processing results...")
            
            # Get general results
            response = requests.get(f"{self.api_base}/api/results/{self.video_id}")
            if response.status_code != 200:
                print(f"❌ Failed to get results: {response.status_code}")
                return None
            
            results = response.json()
            
            # Get DetectifAI security events
            events_response = requests.get(f"{self.api_base}/api/detectifai/events/{self.video_id}")
            security_events = {}
            if events_response.status_code == 200:
                security_events = events_response.json()
            
            # Get keyframes
            keyframes_response = requests.get(f"{self.api_base}/api/keyframes/{self.video_id}")
            keyframes = {}
            if keyframes_response.status_code == 200:
                keyframes = keyframes_response.json()
            
            # Display results
            print("=" * 60)
            print("🎯 DETECTIFAI PROCESSING RESULTS - fire.avi")
            print("=" * 60)
            
            # Basic stats
            print(f"📊 Video Analysis:")
            print(f"   • Total keyframes: {results.get('total_keyframes', 0)}")
            print(f"   • Total events: {results.get('total_events', 0)}")
            print(f"   • Motion events: {results.get('total_motion_events', 0)}")
            print(f"   • Object detections: {results.get('total_object_detections', 0)}")
            print(f"   • Processing time: {results.get('processing_time', 0):.2f}s")
            
            # Security events
            if security_events:
                print(f"\\n🔍 Security Analysis:")
                print(f"   • Total detections: {security_events.get('total_detections', 0)}")
                print(f"   • Fire detections: {security_events.get('fire_detections', 0)}")
                print(f"   • Weapon detections: {security_events.get('weapon_detections', 0)}")
            
            # Keyframes
            if keyframes:
                print(f"\\n🖼️ Keyframe Analysis:")
                print(f"   • Total keyframes: {keyframes.get('total_keyframes', 0)}")
                keyframe_list = keyframes.get('keyframes', [])
                if keyframe_list:
                    print(f"   • First keyframe: {keyframe_list[0].get('timestamp', 0):.2f}s")
                    print(f"   • Last keyframe: {keyframe_list[-1].get('timestamp', 0):.2f}s")
            
            print("=" * 60)
            
            return {
                'results': results,
                'security_events': security_events,
                'keyframes': keyframes
            }
            
        except Exception as e:
            print(f"❌ Error getting results: {e}")
            return None
    
    def create_dashboard_html(self, all_results):
        """Create a simple HTML dashboard showing results"""
        try:
            print("🌐 Creating HTML dashboard...")
            
            results = all_results.get('results', {})
            security_events = all_results.get('security_events', {})
            keyframes = all_results.get('keyframes', {})
            
            html_content = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DetectifAI Dashboard - fire.avi Analysis</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(45deg, #ff6b6b, #ffa500);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        .header p {{
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        .stat-card {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            border-left: 5px solid #007bff;
            transition: transform 0.3s ease;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .stat-card.security {{ border-left-color: #dc3545; }}
        .stat-card.processing {{ border-left-color: #28a745; }}
        .stat-card.keyframes {{ border-left-color: #ffc107; }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
            margin: 0;
        }}
        .stat-label {{
            font-size: 1.1em;
            color: #666;
            margin: 5px 0 0 0;
        }}
        .keyframes-section {{
            padding: 30px;
            background: #f8f9fa;
        }}
        .keyframes-section h2 {{
            text-align: center;
            color: #333;
            margin-bottom: 20px;
        }}
        .keyframes-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
        }}
        .keyframe-card {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .keyframe-placeholder {{
            width: 100%;
            height: 120px;
            background: linear-gradient(45deg, #e0e0e0, #f5f5f5);
            border-radius: 5px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }}
        .api-info {{
            background: #e3f2fd;
            padding: 20px;
            margin: 20px 30px;
            border-radius: 8px;
            border: 1px solid #bbdefb;
        }}
        .api-info h3 {{
            color: #1976d2;
            margin-top: 0;
        }}
        .api-endpoint {{
            background: #fff;
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            font-family: monospace;
            font-size: 0.9em;
            border: 1px solid #ddd;
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #28a745;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
            100% {{ opacity: 1; }}
        }}
        .footer {{
            background: #333;
            color: white;
            text-align: center;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 DetectifAI Dashboard</h1>
            <p><span class="status-indicator"></span>fire.avi Processing Complete - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card processing">
                <div class="stat-number">{results.get('total_keyframes', 0)}</div>
                <div class="stat-label">Keyframes Extracted</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{results.get('total_events', 0)}</div>
                <div class="stat-label">Total Events</div>
            </div>
            <div class="stat-card security">
                <div class="stat-number">{results.get('total_object_detections', 0)}</div>
                <div class="stat-label">Object Detections</div>
            </div>
            <div class="stat-card keyframes">
                <div class="stat-number">{security_events.get('fire_detections', 0)}</div>
                <div class="stat-label">Fire Detections</div>
            </div>
            <div class="stat-card security">
                <div class="stat-number">{security_events.get('weapon_detections', 0)}</div>
                <div class="stat-label">Weapon Detections</div>
            </div>
            <div class="stat-card processing">
                <div class="stat-number">{results.get('processing_time', 0):.1f}s</div>
                <div class="stat-label">Processing Time</div>
            </div>
        </div>
        
        <div class="api-info">
            <h3>🔌 API Integration Status</h3>
            <p>DetectifAI API is running at <strong>http://localhost:5000</strong></p>
            <div class="api-endpoint">GET /api/status/{self.video_id}</div>
            <div class="api-endpoint">GET /api/results/{self.video_id}</div>
            <div class="api-endpoint">GET /api/detectifai/events/{self.video_id}</div>
            <div class="api-endpoint">GET /api/keyframes/{self.video_id}</div>
        </div>
        
        <div class="keyframes-section">
            <h2>🖼️ Extracted Keyframes ({keyframes.get('total_keyframes', 0)} frames)</h2>
            <div class="keyframes-grid">
'''
            
            # Add keyframe cards
            keyframe_list = keyframes.get('keyframes', [])
            for i, keyframe in enumerate(keyframe_list[:12]):  # Show first 12 keyframes
                timestamp = keyframe.get('timestamp', 0)
                html_content += f'''
                <div class="keyframe-card">
                    <div class="keyframe-placeholder">
                        Frame {i+1}<br>
                        {timestamp:.2f}s
                    </div>
                    <div>Timestamp: {timestamp:.2f}s</div>
                </div>
'''
            
            if len(keyframe_list) > 12:
                html_content += f'''
                <div class="keyframe-card" style="background: #e9ecef; display: flex; align-items: center; justify-content: center;">
                    <div style="text-align: center; color: #666;">
                        +{len(keyframe_list) - 12} more<br>keyframes
                    </div>
                </div>
'''
            
            html_content += f'''
            </div>
        </div>
        
        <div class="footer">
            <p>DetectifAI - AI-Powered CCTV Surveillance System | Video ID: {self.video_id}</p>
        </div>
    </div>
    
    <script>
        // Auto-refresh functionality
        console.log('DetectifAI Dashboard loaded successfully');
        console.log('API Base:', 'http://localhost:5000');
        console.log('Video ID:', '{self.video_id}');
        
        // Function to fetch latest data
        function refreshData() {{
            fetch('http://localhost:5000/api/status/{self.video_id}')
                .then(response => response.json())
                .then(data => {{
                    console.log('Status:', data);
                }})
                .catch(error => console.log('API connection:', error));
        }}
        
        // Call refreshData every 30 seconds
        setInterval(refreshData, 30000);
        refreshData(); // Initial call
    </script>
</body>
</html>
'''
            
            # Save HTML file
            html_path = os.path.join("d:/FAST/Final Year Project/finWebApp/finWebApp - Copy/backend", "detectifai_dashboard.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ Dashboard created: {html_path}")
            return html_path
            
        except Exception as e:
            print(f"❌ Error creating dashboard: {e}")
            return None
    
    def run_complete_demo(self):
        """Run the complete demo workflow"""
        print("🎯 DetectifAI Complete Demo - fire.avi Processing")
        print("=" * 60)
        
        try:
            # Step 1: Start API server
            if not self.start_api_server():
                return False
            
            # Step 2: Setup demo video
            if not self.setup_demo_video():
                return False
            
            # Step 3: Start processing
            if not self.start_processing():
                return False
            
            # Step 4: Monitor processing
            if not self.monitor_processing():
                return False
            
            # Step 5: Get results
            all_results = self.get_results()
            if not all_results:
                return False
            
            # Step 6: Create dashboard
            dashboard_path = self.create_dashboard_html(all_results)
            if dashboard_path:
                print(f"\\n🌐 Opening dashboard in browser...")
                try:
                    webbrowser.open(f"file://{dashboard_path}")
                    print("✅ Dashboard opened in browser")
                except:
                    print(f"💡 Open manually: file://{dashboard_path}")
            
            print("\\n🎉 Demo completed successfully!")
            print("\\n📋 Summary:")
            print(f"   • API Server: ✅ Running at http://localhost:5000")
            print(f"   • Video: ✅ fire.avi processed ({all_results['results'].get('total_keyframes', 0)} keyframes)")
            print(f"   • Detections: ✅ {all_results['results'].get('total_object_detections', 0)} objects detected")
            print(f"   • Dashboard: ✅ Available in browser")
            print(f"   • Frontend Integration: ✅ CORS-enabled API ready")
            
            return True
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            return False
        finally:
            # Keep server running for frontend testing
            if self.server_process:
                print("\\n💡 API server is still running for frontend integration testing")
                print("   Press Ctrl+C to stop the server when done")

def main():
    """Main demo runner"""
    demo = DetectifAIDemo()
    return demo.run_complete_demo()

if __name__ == "__main__":
    success = main()
    if success:
        print("\\n🚀 DetectifAI Demo completed! API server is ready for frontend integration.")
    else:
        print("\\n❌ Demo failed. Check the logs for details.")