"""
DetectifAI Complete Video Processing Pipeline

This is the main pipeline that orchestrates all DetectifAI components:
- Optimized video processing with selective frame enhancement
- DetectifAI event detection and security analysis
- Object detection with fire/weapon recognition
- Event aggregation and threat assessment
- Highlight reel generation for security incidents
- Compression and comprehensive reporting
- API integration for real-time frontend updates
"""

import os
import time
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import json

# Import all components
from config import VideoProcessingConfig, get_robbery_detection_config, get_high_recall_config
from core.video_processing import OptimizedVideoProcessor
from event_aggregation import EventDetector, EventDeduplicationEngine
from video_segmentation import VideoSegmentationEngine
from highlight_reel import HighlightReelGenerator
from video_compression import VideoCompressor
from json_reports import ReportGenerator
from object_detection import ObjectDetectionIntegrator
from detectifai_events import DetectifAIEventType, ThreatLevel

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/detectifai_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

class CompleteVideoProcessingPipeline:
    """Complete video processing pipeline orchestrating all components"""
    
    def __init__(self, config: VideoProcessingConfig = None):
        """
        Initialize the complete processing pipeline
        
        Args:
            config: VideoProcessingConfig object, uses default if None
        """
        self.config = config or VideoProcessingConfig()
        self.processing_stats = {
            'start_time': None,
            'end_time': None,
            'total_processing_time': 0,
            'component_times': {},
            'memory_usage': {},
            'errors': []
        }
        
        # Initialize components
        logger.info("Initializing video processing pipeline components")
        
        try:
            self.video_processor = OptimizedVideoProcessor(self.config)
            self.event_detector = EventDetector(self.config)
            self.deduplication_engine = EventDeduplicationEngine(self.config)
            self.segmentation_engine = VideoSegmentationEngine(self.config)
            self.highlight_generator = HighlightReelGenerator(self.config)
            self.compressor = VideoCompressor(self.config)
            self.report_generator = ReportGenerator(self.config)
            self.object_detector = ObjectDetectionIntegrator(self.config)
            
            logger.info("✅ All pipeline components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize pipeline components: {e}")
            raise
    
    def process_video_complete(self, video_path: str, output_name: str = None) -> Dict[str, Any]:
        """
        Process video through complete pipeline
        
        Args:
            video_path: Path to input video file
            output_name: Optional custom output name (uses video filename if None)
            
        Returns:
            Dictionary containing all processing results and output paths
        """
        logger.info(f"🚀 Starting complete video processing pipeline")
        logger.info(f"📁 Input video: {video_path}")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Initialize processing stats
        self.processing_stats['start_time'] = time.time()
        
        # Prepare output naming
        if output_name is None:
            output_name = os.path.splitext(os.path.basename(video_path))[0]
        
        results = {
            'input_video': video_path,
            'output_name': output_name,
            'config_used': self.config.__dict__.copy(),
            'processing_stats': self.processing_stats,
            'outputs': {}
        }
        # Ensure there is a concrete output directory for this run so downstream
        # steps (annotated video creation, reports, etc.) can write reliably.
        output_dir = os.path.join(self.config.output_base_dir, output_name)
        os.makedirs(output_dir, exist_ok=True)
        results['outputs']['output_directory'] = output_dir
        
        try:
            # Step 1: Extract keyframes with adaptive enhancement
            logger.info("🎬 Step 1: Extracting keyframes with adaptive enhancement...")
            step_start = time.time()
            
            keyframes = self.video_processor.extract_keyframes(video_path)
            
            self.processing_stats['component_times']['keyframe_extraction'] = time.time() - step_start
            results['outputs']['total_keyframes'] = len(keyframes)
            
            logger.info(f"✅ Extracted {len(keyframes)} keyframes")
            
            # Step 2: Create video segments
            logger.info("📊 Step 2: Creating video segments...")
            step_start = time.time()
            
            segments = self.segmentation_engine.create_video_segments(video_path, keyframes)
            
            self.processing_stats['component_times']['segmentation'] = time.time() - step_start
            results['outputs']['total_segments'] = len(segments)
            
            logger.info(f"✅ Created {len(segments)} video segments")
            
            # Step 3: Object Detection (if enabled)
            detection_results = []
            object_events = []
            if self.config.enable_object_detection:
                logger.info("🎯 Step 3a: Running object detection...")
                step_start = time.time()
                
                detection_results, object_events = self.object_detector.process_keyframes_with_object_detection(keyframes)
                
                self.processing_stats['component_times']['object_detection'] = time.time() - step_start
                results['outputs']['total_object_detections'] = len(detection_results)
                results['outputs']['total_object_events'] = len(object_events)
                
                logger.info(f"✅ Object detection complete: {len(object_events)} object-based events created")
            
            # Step 4: Detect motion-based events
            logger.info("🎯 Step 4: Detecting motion-based events...")
            step_start = time.time()
            
            motion_events = self.event_detector.detect_events(keyframes)
            
            self.processing_stats['component_times']['event_detection'] = time.time() - step_start
            
            # Convert object events to standard format and combine
            standard_object_events = []
            if object_events:
                standard_object_events = self.event_detector.convert_object_events_to_standard_format(object_events)
            
            all_events = motion_events + standard_object_events
            results['outputs']['total_motion_events'] = len(motion_events)
            results['outputs']['total_events'] = len(all_events)
            
            logger.info(f"✅ Detected {len(motion_events)} motion events + {len(object_events)} object events = {len(all_events)} total events")
            
            # Step 4.5: DetectifAI Security Event Processing (includes facial recognition)
            logger.info("🔍 Step 4.5: DetectifAI Security Event Processing...")
            step_start = time.time()
            
            detectifai_events = []
            facial_recognition_stats = {}
            
            try:
                from detectifai_events import DetectifAIEventProcessor
                
                detectifai_processor = DetectifAIEventProcessor(self.config)
                detectifai_events = detectifai_processor.process_security_events(
                    keyframes=keyframes,
                    motion_events=motion_events,
                    object_events=object_events
                )
                
                # Additional facial recognition processing if available
                try:
                    from facial_recognition import FacialRecognitionPlaceholder
                    
                    if hasattr(self.config, 'enable_facial_recognition') and self.config.enable_facial_recognition:
                        logger.info("👤 Processing facial recognition for suspicious person tracking...")
                        face_detector = FacialRecognitionPlaceholder(self.config)
                        
                        # Analyze keyframes for faces
                        face_results = face_detector.analyze_keyframes_for_faces(keyframes, detectifai_events)
                        
                        # Track suspicious persons and detect re-occurrences
                        if face_results:
                            reoccurrence_events = face_detector.track_suspicious_persons(face_results, detectifai_events)
                            
                            # Convert re-occurrence events to DetectifAI format
                            for reoccurrence in reoccurrence_events:
                                # Create DetectifAI event from reoccurrence
                                from detectifai_events import DetectifAIEvent, DetectifAIEventType, ThreatLevel
                                
                                detectifai_reoccurrence = DetectifAIEvent(
                                    event_id=reoccurrence['event_id'],
                                    event_type=DetectifAIEventType.SUSPICIOUS_PERSON_REOCCURRENCE,
                                    threat_level=ThreatLevel.HIGH,
                                    start_timestamp=reoccurrence['start_timestamp'],
                                    end_timestamp=reoccurrence['end_timestamp'],
                                    confidence=reoccurrence.get('max_confidence', reoccurrence['confidence']),
                                    keyframes=reoccurrence['keyframes'],
                                    importance_score=reoccurrence.get('importance_score', 4.0),
                                    detection_data={
                                        'person_details': reoccurrence.get('detection_details', {}),
                                        'placeholder': True
                                    },
                                    requires_immediate_response=True,
                                    investigation_priority=5.0,
                                    description=reoccurrence.get('description', 'Suspicious person re-occurrence detected'),
                                    processing_timestamp=time.time(),
                                    detection_model_used='facial_recognition_placeholder'
                                )
                                
                                detectifai_events.append(detectifai_reoccurrence)
                                logger.info(f"Added facial recognition event: {detectifai_reoccurrence.event_id}")
                        
                        facial_recognition_stats = face_detector.get_detection_stats()
                
                except ImportError:
                    logger.info("Facial recognition module not available - skipping")
                except Exception as e:
                    logger.error(f"Error in facial recognition processing: {e}")
                    facial_recognition_stats = {'error': str(e)}
            
            except ImportError:
                logger.info("DetectifAI events module not available - using standard event processing")
            
            self.processing_stats['component_times']['detectifai_processing'] = time.time() - step_start
            results['outputs']['detectifai_events'] = len(detectifai_events)
            results['outputs']['facial_recognition_stats'] = facial_recognition_stats
            
            logger.info(f"✅ DetectifAI processing complete: {len(detectifai_events)} security events created")

            # Step 5: Deduplicate events and create canonical events
            logger.info("🔄 Step 5: Deduplicating events...")
            step_start = time.time()
            
            canonical_events, dedup_stats = self.deduplication_engine.deduplicate_events(all_events)
            
            self.processing_stats['component_times']['deduplication'] = time.time() - step_start
            results['outputs']['canonical_events'] = len(canonical_events)
            results['outputs']['deduplication_stats'] = dedup_stats
            
            logger.info(f"✅ Created {len(canonical_events)} canonical events")
            
            # Step 5: Generate highlight reels
            logger.info("🎥 Step 5: Generating highlight reels...")
            step_start = time.time()
            
            highlight_paths = self._generate_all_highlight_reels(segments, canonical_events)
            results['outputs']['highlight_reels'] = highlight_paths
            
            self.processing_stats['component_times']['highlight_generation'] = time.time() - step_start
            
            logger.info(f"✅ Generated {len(highlight_paths)} highlight reels")
            
            # Step 5.5: Create annotated video with bounding boxes (if detections exist)
            annotated_video_path = None
            if self.config.enable_object_detection and detection_results:
                logger.info("🎨 Step 5.5: Creating annotated video with bounding boxes...")
                step_start = time.time()
                
                try:
                    # Create annotated video with detection bounding boxes
                    annotated_output_path = os.path.join(
                        results['outputs']['output_directory'], 
                        f"{output_name}_annotated.mp4"
                    )
                    
                    annotated_video_path = self.object_detector.create_annotated_video(
                        video_path, 
                        detection_results,
                        annotated_output_path
                    )
                    
                    self.processing_stats['component_times']['video_annotation'] = time.time() - step_start
                    
                    if annotated_video_path:
                        logger.info(f"✅ Annotated video created: {annotated_video_path}")
                        results['outputs']['annotated_video'] = annotated_video_path
                    else:
                        logger.warning("⚠️ Annotated video creation failed")
                        
                except Exception as e:
                    logger.error(f"Error creating annotated video: {str(e)}")
            
            # Step 6: Compress video
            if self.config.generate_compressed_video:
                logger.info("🗜️  Step 6: Compressing video...")
                step_start = time.time()
                
                # Compress the annotated video if it exists, otherwise compress original
                video_to_compress = annotated_video_path if annotated_video_path else video_path
                
                compressed_path = self.compressor.compress_video(
                    video_to_compress, 
                    f"{output_name}_compressed.{self.config.video_output_format}"
                )
                
                results['outputs']['compressed_video'] = compressed_path
                self.processing_stats['component_times']['compression'] = time.time() - step_start
                
                if compressed_path:
                    logger.info(f"✅ Video compressed: {compressed_path}")
                else:
                    logger.warning("⚠️ Video compression failed")
            
            # Step 7: Generate reports
            logger.info("📋 Step 7: Generating reports...")
            step_start = time.time()
            
            report_paths = self._generate_all_reports(keyframes, all_events, canonical_events, segments, detection_results)
            results['outputs']['reports'] = report_paths
            
            self.processing_stats['component_times']['report_generation'] = time.time() - step_start
            
            logger.info(f"✅ Generated {len(report_paths)} reports")
            
            # Step 8: Save segment files
            if self.config.generate_segments:
                logger.info("💾 Step 8: Saving segment files...")
                
                segments_report_path = self.segmentation_engine.save_segments_metadata(
                    segments, 
                    os.path.join(self.config.output_base_dir, "reports", "video_segments.json")
                )
                
                individual_segments_saved = self.segmentation_engine.save_individual_segment_files(segments)
                
                results['outputs']['segments_saved'] = individual_segments_saved
                
                logger.info("✅ Segment files saved")
            
            # Finalize processing stats
            self.processing_stats['end_time'] = time.time()
            self.processing_stats['total_processing_time'] = (
                self.processing_stats['end_time'] - self.processing_stats['start_time']
            )
            
            logger.info(f"🎉 PIPELINE COMPLETE!")
            logger.info(f"⏱️  Total processing time: {self.processing_stats['total_processing_time']:.2f} seconds")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Pipeline processing failed: {e}")
            self.processing_stats['errors'].append(str(e))
            raise
    
    def _generate_all_highlight_reels(self, segments: List, canonical_events: List) -> Dict[str, str]:
        """Generate all types of highlight reels"""
        highlight_paths = {}
        
        try:
            # Event-aware highlight reel
            event_aware_path = self.highlight_generator.create_event_aware_highlight_reel(
                segments, canonical_events
            )
            if event_aware_path:
                highlight_paths['event_aware'] = event_aware_path
            
            # Ultra-comprehensive highlight reel
            comprehensive_path = self.highlight_generator.create_ultra_comprehensive_highlight_reel(segments)
            if comprehensive_path:
                highlight_paths['ultra_comprehensive'] = comprehensive_path
            
            # Quality-focused highlight reel
            quality_path = self.highlight_generator.create_quality_focused_highlight_reel(segments)
            if quality_path:
                highlight_paths['quality_focused'] = quality_path
                
        except Exception as e:
            logger.error(f"Error generating highlight reels: {e}")
            self.processing_stats['errors'].append(f"Highlight generation error: {e}")
        
        return highlight_paths
    
    def _generate_all_reports(self, keyframes: List, events: List, 
                            canonical_events: List, segments: List, 
                            detection_results: List = None) -> Dict[str, str]:
        """Generate all types of reports"""
        report_paths = {}
        
        try:
            # Processing results report (enhanced with object detection)
            processing_report = self.report_generator.generate_processing_results_report(
                keyframes, events, canonical_events, segments, self.processing_stats, detection_results
            )
            if processing_report:
                report_paths['processing_results'] = processing_report
            
            # Canonical events report
            canonical_report = self.report_generator.generate_canonical_events_report(canonical_events)
            if canonical_report:
                report_paths['canonical_events'] = canonical_report
            
            # Segments report
            segments_report = self.report_generator.generate_segments_report(segments)
            if segments_report:
                report_paths['video_segments'] = segments_report
            
            # Object detection report (if enabled)
            if self.config.enable_object_detection and detection_results:
                object_detection_report = self.report_generator.generate_object_detection_report(
                    detection_results, self.object_detector.get_object_detection_summary()
                )
                if object_detection_report:
                    report_paths['object_detection'] = object_detection_report
            
            # HTML gallery (enhanced with object detection)
            if self.config.generate_html_gallery:
                html_gallery = self.report_generator.generate_html_gallery(
                    keyframes, canonical_events, segments, detection_results
                )
                if html_gallery:
                    report_paths['html_gallery'] = html_gallery
                    
        except Exception as e:
            logger.error(f"Error generating reports: {e}")
            self.processing_stats['errors'].append(f"Report generation error: {e}")
        
        return report_paths
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of processing results"""
        return {
            'total_processing_time': self.processing_stats.get('total_processing_time', 0),
            'component_times': self.processing_stats.get('component_times', {}),
            'errors_encountered': len(self.processing_stats.get('errors', [])),
            'processing_config': {
                'base_quality_threshold': self.config.base_quality_threshold,
                'motion_threshold': self.config.motion_threshold,
                'max_summary_frames': self.config.max_summary_frames,
                'output_resolution': self.config.output_resolution
            }
        }
    
    def process_multiple_videos(self, video_directory: str) -> Dict[str, Dict[str, Any]]:
        """
        Process multiple videos in a directory
        
        Args:
            video_directory: Directory containing video files
            
        Returns:
            Dictionary mapping video paths to processing results
        """
        logger.info(f"🎬 Processing multiple videos from: {video_directory}")
        
        if not os.path.exists(video_directory):
            raise FileNotFoundError(f"Video directory not found: {video_directory}")
        
        # Find video files
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
        video_files = []
        
        for filename in os.listdir(video_directory):
            if any(filename.lower().endswith(ext) for ext in video_extensions):
                video_files.append(os.path.join(video_directory, filename))
        
        logger.info(f"Found {len(video_files)} video files to process")
        
        batch_results = {}
        successful_count = 0
        
        for i, video_path in enumerate(video_files, 1):
            try:
                logger.info(f"📹 Processing video {i}/{len(video_files)}: {os.path.basename(video_path)}")
                
                results = self.process_video_complete(video_path)
                batch_results[video_path] = results
                successful_count += 1
                
                logger.info(f"✅ Successfully processed {os.path.basename(video_path)}")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {os.path.basename(video_path)}: {e}")
                batch_results[video_path] = {'error': str(e)}
        
        logger.info(f"🎉 Batch processing complete: {successful_count}/{len(video_files)} successful")
        
        return batch_results


def main():
    """Main function demonstrating pipeline usage"""
    
    # Example usage with different configurations
    
    print("🎬 Video Processing Pipeline Demo")
    print("=" * 50)
    
    # For robbery/crime detection - use specialized config
    robbery_config = get_robbery_detection_config()
    pipeline_robbery = CompleteVideoProcessingPipeline(robbery_config)
    
    # For high recall (more keyframes) - use high recall config
    high_recall_config = get_high_recall_config()
    pipeline_high_recall = CompleteVideoProcessingPipeline(high_recall_config)
    
    # Example video processing
    video_file = "rob.mp4"  # Replace with your video file
    
    if os.path.exists(video_file):
        print(f"\\n🎯 Processing with robbery detection config...")
        results = pipeline_robbery.process_video_complete(video_file)
        
        print(f"\\n📊 Processing Summary:")
        summary = pipeline_robbery.get_processing_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
            
        print(f"\\n📁 Output files created:")
        for category, outputs in results['outputs'].items():
            if isinstance(outputs, dict):
                print(f"  {category}:")
                for name, path in outputs.items():
                    print(f"    - {name}: {path}")
            else:
                print(f"  {category}: {outputs}")
    else:
        print(f"❌ Video file not found: {video_file}")
        print("\\n💡 Available configuration presets:")
        print("  - get_robbery_detection_config() - Optimized for crime/event detection")
        print("  - get_high_recall_config() - More keyframes, sensitive detection") 
        print("  - get_high_precision_config() - Fewer but higher quality keyframes")
        print("  - get_balanced_config() - General purpose settings")


if __name__ == "__main__":
    main()