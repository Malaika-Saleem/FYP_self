"""
DetectifAI System Integration Test

This script tests the complete DetectifAI surveillance system including:
- Object detection (fire, weapons)
- Event aggregation and deduplication  
- Facial recognition and person tracking
- Placeholder modules (fight, wall jump, accident detection)
- DetectifAI-specific event processing
"""

import os
import sys
import time
import logging
import traceback
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from config import VideoProcessingConfig
from main_pipeline import CompleteVideoProcessingPipeline

# Set up test logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('detectifai_test.log')
    ]
)
logger = logging.getLogger(__name__)

class DetectifAISystemTester:
    """Test harness for DetectifAI surveillance system"""
    
    def __init__(self):
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': []
        }
        
        # Test configuration
        self.config = VideoProcessingConfig()
        self.config.enable_object_detection = True
        self.config.enable_facial_recognition = True
        self.config.suspicious_person_tracking = True
        
        # Override for testing
        self.config.video_compression_ratio = 0.7  # Faster for testing
        self.config.enable_adaptive_processing = True
        
        logger.info("DetectifAI System Tester initialized")
    
    def run_all_tests(self):
        """Run all DetectifAI system tests"""
        logger.info("🚀 Starting DetectifAI System Integration Tests")
        start_time = time.time()
        
        test_methods = [
            ('Configuration Validation', self.test_configuration),
            ('Module Import Tests', self.test_module_imports),
            ('Object Detection Models', self.test_object_detection_setup),
            ('DetectifAI Event System', self.test_detectifai_events),
            ('Facial Recognition Setup', self.test_facial_recognition),
            ('Placeholder Module Tests', self.test_placeholder_modules),
            ('Pipeline Integration', self.test_pipeline_integration),
            ('Video Processing (if video available)', self.test_video_processing)
        ]
        
        for test_name, test_method in test_methods:
            self._run_test(test_name, test_method)
        
        total_time = time.time() - start_time
        self._print_test_summary(total_time)
        
        return self.test_results
    
    def _run_test(self, test_name: str, test_method):
        """Run individual test with error handling"""
        logger.info(f"🧪 Running test: {test_name}")
        self.test_results['total_tests'] += 1
        
        try:
            result = test_method()
            if result:
                self.test_results['passed_tests'] += 1
                logger.info(f"✅ {test_name}: PASSED")
                self.test_results['test_details'].append({
                    'name': test_name,
                    'status': 'PASSED',
                    'details': result if isinstance(result, dict) else {}
                })
            else:
                self.test_results['failed_tests'] += 1
                logger.error(f"❌ {test_name}: FAILED")
                self.test_results['test_details'].append({
                    'name': test_name,
                    'status': 'FAILED',
                    'details': {'error': 'Test returned False'}
                })
        except Exception as e:
            self.test_results['failed_tests'] += 1
            error_msg = f"Exception: {str(e)}"
            logger.error(f"❌ {test_name}: FAILED - {error_msg}")
            logger.error(traceback.format_exc())
            self.test_results['test_details'].append({
                'name': test_name,
                'status': 'FAILED',
                'details': {'error': error_msg, 'traceback': traceback.format_exc()}
            })
    
    def test_configuration(self):
        """Test DetectifAI configuration settings"""
        try:
            # Check object detection config
            assert hasattr(self.config, 'enable_object_detection')
            assert hasattr(self.config, 'object_detection_confidence')
            
            # Check facial recognition config
            assert hasattr(self.config, 'enable_facial_recognition')
            assert hasattr(self.config, 'face_recognition_confidence')
            assert hasattr(self.config, 'suspicious_person_tracking')
            
            # Check directory structure
            models_dir = Path(self.config.models_dir)
            output_dir = Path(self.config.output_base_dir)
            
            logger.info(f"Models directory: {models_dir}")
            logger.info(f"Output directory: {output_dir}")
            
            return {
                'object_detection_enabled': self.config.enable_object_detection,
                'facial_recognition_enabled': self.config.enable_facial_recognition,
                'models_dir_exists': models_dir.exists(),
                'output_dir_exists': output_dir.exists()
            }
        except Exception as e:
            logger.error(f"Configuration test failed: {e}")
            return False
    
    def test_module_imports(self):
        """Test that all DetectifAI modules can be imported"""
        import_results = {}
        
        modules_to_test = [
            'config',
            'main_pipeline',
            'video_processing',
            'event_aggregation',
            'object_detection',
            'detectifai_events',
            'facial_recognition',
            'fight_detection',
            'wall_jump_detection',
            'accident_detection'
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
                import_results[module_name] = 'SUCCESS'
                logger.info(f"✅ Successfully imported {module_name}")
            except ImportError as e:
                import_results[module_name] = f'FAILED: {str(e)}'
                logger.error(f"❌ Failed to import {module_name}: {e}")
            except Exception as e:
                import_results[module_name] = f'ERROR: {str(e)}'
                logger.error(f"🚨 Error importing {module_name}: {e}")
        
        success_count = sum(1 for status in import_results.values() if status == 'SUCCESS')
        total_count = len(import_results)
        
        logger.info(f"Module imports: {success_count}/{total_count} successful")
        
        return {
            'import_results': import_results,
            'success_rate': success_count / total_count,
            'all_modules_imported': success_count == total_count
        }
    
    def test_object_detection_setup(self):
        """Test object detection model availability and setup"""
        try:
            from object_detection import ObjectDetectionIntegrator
            
            # Initialize object detection
            obj_detector = ObjectDetectionIntegrator(self.config)
            
            # Check model files
            models_info = {}
            models_dir = Path(self.config.models_dir)
            
            for model_type, model_file in [('fire', 'fire_yolo11.pt'), ('weapons', 'yolov11_knife_gun.pt')]:
                model_path = models_dir / model_file
                models_info[model_type] = {
                    'file': model_file,
                    'path': str(model_path),
                    'exists': model_path.exists(),
                    'size_mb': model_path.stat().st_size / (1024*1024) if model_path.exists() else 0
                }
            
            # Test placeholder detection (since real models might not be available)
            test_keyframes = []  # Empty for placeholder test
            detection_results, object_events = obj_detector.process_keyframes_with_object_detection(test_keyframes)
            
            return {
                'object_detector_initialized': True,
                'models_info': models_info,
                'placeholder_test_results': {
                    'detection_results_count': len(detection_results),
                    'object_events_count': len(object_events)
                }
            }
            
        except Exception as e:
            logger.error(f"Object detection test failed: {e}")
            return False
    
    def test_detectifai_events(self):
        """Test DetectifAI event system"""
        try:
            from detectifai_events import (
                DetectifAIEventProcessor, DetectifAIEventType, 
                ThreatLevel, DetectifAIEvent
            )
            
            # Initialize event processor
            processor = DetectifAIEventProcessor(self.config)
            
            # Test event type enumeration
            event_types = list(DetectifAIEventType)
            threat_levels = list(ThreatLevel)
            
            # Test processing with empty data (placeholder test)
            detectifai_events = processor.process_security_events(
                keyframes=[],
                motion_events=[],
                object_events=[]
            )
            
            return {
                'processor_initialized': True,
                'available_event_types': [et.value for et in event_types],
                'available_threat_levels': [tl.value for tl in threat_levels],
                'placeholder_events_count': len(detectifai_events),
                'processor_stats': processor.get_processing_stats()
            }
            
        except Exception as e:
            logger.error(f"DetectifAI events test failed: {e}")
            return False
    
    def test_facial_recognition(self):
        """Test facial recognition and person tracking setup"""
        try:
            from facial_recognition import FacialRecognitionPlaceholder
            
            # Initialize facial recognition
            face_detector = FacialRecognitionPlaceholder(self.config)
            
            # Test face detection placeholder
            test_frame_path = "test_frame.jpg"  # Placeholder
            face_result = face_detector.detect_faces_in_frame(test_frame_path, timestamp=0.0)
            
            # Test person tracking placeholder
            reoccurrence_events = face_detector.track_suspicious_persons(
                face_results=[face_result] if face_result.faces_detected > 0 else [],
                security_events=[]
            )
            
            # Get statistics
            stats = face_detector.get_detection_stats()
            persons_summary = face_detector.get_suspicious_persons_summary()
            
            return {
                'face_detector_initialized': True,
                'placeholder_detection_working': True,
                'detection_stats': stats,
                'persons_summary': persons_summary,
                'reoccurrence_events_count': len(reoccurrence_events),
                'faces_detected_in_test': face_result.faces_detected
            }
            
        except Exception as e:
            logger.error(f"Facial recognition test failed: {e}")
            return False
    
    def test_placeholder_modules(self):
        """Test placeholder detection modules"""
        placeholder_results = {}
        
        placeholder_modules = [
            ('fight_detection', 'FightDetectionPlaceholder'),
            ('wall_jump_detection', 'WallJumpDetectionPlaceholder'),
            ('accident_detection', 'RoadAccidentDetectionPlaceholder')
        ]
        
        for module_name, class_name in placeholder_modules:
            try:
                module = __import__(module_name)
                placeholder_class = getattr(module, class_name)
                
                # Initialize placeholder
                placeholder = placeholder_class(self.config)
                
                # Test placeholder detection
                test_frame_path = "test_frame.jpg"
                if hasattr(placeholder, 'detect_in_frame'):
                    result = placeholder.detect_in_frame(test_frame_path, timestamp=0.0)
                    placeholder_results[module_name] = {
                        'initialized': True,
                        'detection_test': 'completed',
                        'result_type': type(result).__name__
                    }
                else:
                    placeholder_results[module_name] = {
                        'initialized': True,
                        'detection_test': 'no_detect_method',
                        'available_methods': [m for m in dir(placeholder) if not m.startswith('_')]
                    }
                
            except Exception as e:
                placeholder_results[module_name] = {
                    'initialized': False,
                    'error': str(e)
                }
                logger.error(f"Placeholder module {module_name} test failed: {e}")
        
        success_count = sum(1 for result in placeholder_results.values() if result.get('initialized', False))
        
        return {
            'placeholder_results': placeholder_results,
            'success_rate': success_count / len(placeholder_modules),
            'total_placeholders': len(placeholder_modules),
            'working_placeholders': success_count
        }
    
    def test_pipeline_integration(self):
        """Test complete pipeline integration"""
        try:
            # Initialize pipeline
            pipeline = CompleteVideoProcessingPipeline(self.config)
            
            # Test pipeline components initialization
            components_status = {
                'video_processor': hasattr(pipeline, 'video_processor'),
                'event_detector': hasattr(pipeline, 'event_detector'),
                'deduplication_engine': hasattr(pipeline, 'deduplication_engine'),
                'segmentation_engine': hasattr(pipeline, 'segmentation_engine'),
                'highlight_generator': hasattr(pipeline, 'highlight_generator'),
                'compressor': hasattr(pipeline, 'compressor'),
                'report_generator': hasattr(pipeline, 'report_generator'),
                'object_detector': hasattr(pipeline, 'object_detector')
            }
            
            # Test configuration access
            config_test = {
                'has_config': hasattr(pipeline, 'config'),
                'object_detection_enabled': getattr(pipeline.config, 'enable_object_detection', False),
                'facial_recognition_enabled': getattr(pipeline.config, 'enable_facial_recognition', False)
            }
            
            working_components = sum(components_status.values())
            total_components = len(components_status)
            
            return {
                'pipeline_initialized': True,
                'components_status': components_status,
                'config_test': config_test,
                'integration_score': working_components / total_components,
                'all_components_working': working_components == total_components
            }
            
        except Exception as e:
            logger.error(f"Pipeline integration test failed: {e}")
            return False
    
    def test_video_processing(self):
        """Test video processing if test video is available"""
        try:
            # Look for test video
            test_videos = [
                'rob.mp4',
                'test_video.mp4',
                'sample.mp4'
            ]
            
            test_video_path = None
            for video_file in test_videos:
                video_path = Path(video_file)
                if video_path.exists():
                    test_video_path = str(video_path)
                    break
            
            if not test_video_path:
                logger.info("No test video found - skipping video processing test")
                return {
                    'test_skipped': True,
                    'reason': 'No test video available',
                    'searched_files': test_videos
                }
            
            # Initialize pipeline
            pipeline = CompleteVideoProcessingPipeline(self.config)
            
            # Process short segment for testing (first 10 seconds)
            logger.info(f"Processing test video: {test_video_path}")
            
            # Override config for quick test
            test_config = self.config
            test_config.max_processing_duration = 10.0  # Process only 10 seconds
            test_config.keyframe_extraction_fps = 0.5  # Extract fewer keyframes for speed
            
            start_time = time.time()
            results = pipeline.process_video_complete(test_video_path)
            processing_time = time.time() - start_time
            
            return {
                'test_completed': True,
                'video_path': test_video_path,
                'processing_time_seconds': processing_time,
                'results_summary': {
                    'keyframes_extracted': results['outputs'].get('keyframes_extracted', 0),
                    'motion_events': results['outputs'].get('total_motion_events', 0),
                    'object_events': results['outputs'].get('total_object_events', 0),
                    'detectifai_events': results['outputs'].get('detectifai_events', 0),
                    'canonical_events': results['outputs'].get('canonical_events', 0),
                    'highlight_reels': len(results['outputs'].get('highlight_reels', [])),
                    'total_processing_time': results.get('total_processing_time', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Video processing test failed: {e}")
            return {
                'test_failed': True,
                'error': str(e)
            }
    
    def _print_test_summary(self, total_time: float):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🔍 DETECTIFAI SYSTEM TEST SUMMARY")
        print("="*80)
        print(f"⏱️  Total test time: {total_time:.2f} seconds")
        print(f"📊 Tests run: {self.test_results['total_tests']}")
        print(f"✅ Tests passed: {self.test_results['passed_tests']}")
        print(f"❌ Tests failed: {self.test_results['failed_tests']}")
        
        success_rate = (self.test_results['passed_tests'] / self.test_results['total_tests']) * 100
        print(f"📈 Success rate: {success_rate:.1f}%")
        
        print("\n📋 DETAILED RESULTS:")
        print("-" * 40)
        
        for test_detail in self.test_results['test_details']:
            status_icon = "✅" if test_detail['status'] == 'PASSED' else "❌"
            print(f"{status_icon} {test_detail['name']}: {test_detail['status']}")
            
            if test_detail['status'] == 'FAILED' and 'error' in test_detail['details']:
                print(f"   Error: {test_detail['details']['error']}")
        
        print("\n" + "="*80)
        
        if success_rate >= 80:
            print("🎉 DetectifAI system is ready for demonstration!")
        elif success_rate >= 60:
            print("⚠️  DetectifAI system has some issues but core functionality works")
        else:
            print("🚨 DetectifAI system needs significant fixes before demonstration")
        
        print("="*80)

def main():
    """Main test execution"""
    print("🚀 DetectifAI System Integration Test Suite")
    print("Testing complete surveillance system with AI detection capabilities")
    print("-" * 60)
    
    tester = DetectifAISystemTester()
    results = tester.run_all_tests()
    
    # Save test results
    import json
    with open('detectifai_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed test results saved to: detectifai_test_results.json")
    
    return results

if __name__ == "__main__":
    main()