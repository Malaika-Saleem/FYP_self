"""
Quick Start Example - Video Processing Pipeline

This example shows how to use the video processing pipeline with different configurations.
"""

import os
from main_pipeline import CompleteVideoProcessingPipeline
from config import (
    get_robbery_detection_config, 
    get_high_recall_config, 
    get_high_precision_config,
    get_balanced_config,
    VideoProcessingConfig
)

def process_single_video_example():
    """Example: Process a single video with robbery detection config"""
    
    print("🎬 Single Video Processing Example")
    print("=" * 40)
    
    # Video file path
    video_path = "rob.mp4"  # Change this to your video file
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        print("Please update the video_path variable with your video file")
        return
    
    # Use robbery detection configuration (optimized for crime/event detection)
    config = get_robbery_detection_config()
    
    # Create pipeline
    pipeline = CompleteVideoProcessingPipeline(config)
    
    # Process video
    print(f"🚀 Processing video: {video_path}")
    results = pipeline.process_video_complete(video_path)
    
    # Print results
    print(f"\\n✅ Processing Complete!")
    print(f"📊 Results Summary:")
    print(f"   • Keyframes extracted: {results['outputs']['total_keyframes']}")
    print(f"   • Events detected: {results['outputs']['total_events']}")
    print(f"   • Canonical events: {results['outputs']['canonical_events']}")
    print(f"   • Video segments: {results['outputs']['total_segments']}")
    print(f"   • Processing time: {results['processing_stats']['total_processing_time']:.2f}s")
    
    print(f"\\n📁 Output Files:")
    for category, outputs in results['outputs'].items():
        if isinstance(outputs, dict):
            print(f"   {category.upper()}:")
            for name, path in outputs.items():
                if isinstance(path, str) and path:
                    print(f"     - {name}: {path}")
        elif isinstance(outputs, (int, str)) and outputs:
            print(f"   {category}: {outputs}")

def process_with_custom_config_example():
    """Example: Process video with custom configuration"""
    
    print("\\n🔧 Custom Configuration Example")
    print("=" * 40)
    
    # Create custom configuration
    custom_config = VideoProcessingConfig(
        # More keyframes settings
        base_quality_threshold=0.12,      # Lower = more keyframes
        motion_threshold=0.006,           # Lower = more motion sensitive
        max_summary_frames=25,            # More frames in highlight reel
        
        # Higher quality settings
        enable_clahe=True,                # Enhanced contrast
        compression_crf=20,               # Better compression quality
        output_resolution="1080p",        # High resolution output
        
        # Processing settings
        frame_sampling_interval=0.8,      # More frequent sampling
        temporal_clustering_window=20.0,  # Wider event clustering
    )
    
    video_path = "rob.mp4"  # Change this to your video file
    
    if os.path.exists(video_path):
        pipeline = CompleteVideoProcessingPipeline(custom_config)
        
        print(f"🚀 Processing with custom config...")
        results = pipeline.process_video_complete(video_path)
        
        print(f"✅ Custom processing complete!")
        print(f"📊 Keyframes: {results['outputs']['total_keyframes']}")
        print(f"📊 Events: {results['outputs']['total_events']}")

def compare_configurations_example():
    """Example: Compare different configuration presets"""
    
    print("\\n⚖️  Configuration Comparison Example")
    print("=" * 40)
    
    video_path = "rob.mp4"  # Change this to your video file
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return
    
    # Different configurations to test
    configs = {
        "Robbery Detection": get_robbery_detection_config(),
        "High Recall": get_high_recall_config(),
        "High Precision": get_high_precision_config(),
        "Balanced": get_balanced_config()
    }
    
    results_comparison = {}
    
    for config_name, config in configs.items():
        print(f"\\n🧪 Testing {config_name} configuration...")
        
        pipeline = CompleteVideoProcessingPipeline(config)
        results = pipeline.process_video_complete(video_path, f"test_{config_name.lower().replace(' ', '_')}")
        
        results_comparison[config_name] = {
            'keyframes': results['outputs']['total_keyframes'],
            'events': results['outputs']['total_events'],
            'canonical_events': results['outputs']['canonical_events'],
            'processing_time': results['processing_stats']['total_processing_time']
        }
    
    print(f"\\n📊 CONFIGURATION COMPARISON RESULTS:")
    print(f"{'Configuration':<20} {'Keyframes':<12} {'Events':<8} {'Canonical':<10} {'Time(s)':<8}")
    print("-" * 65)
    
    for config_name, metrics in results_comparison.items():
        print(f"{config_name:<20} {metrics['keyframes']:<12} {metrics['events']:<8} {metrics['canonical_events']:<10} {metrics['processing_time']:<8.1f}")

def parameter_tuning_guide():
    """Show parameter tuning guide"""
    
    print("\\n🔧 PARAMETER TUNING GUIDE")
    print("=" * 50)
    
    print("\\n🎯 FOR MORE KEYFRAMES:")
    print("   • base_quality_threshold: 0.10-0.12 (lower)")
    print("   • motion_threshold: 0.005-0.008 (lower)")
    print("   • max_summary_frames: 20-30 (higher)")
    print("   • frame_sampling_interval: 0.5-1.0 (lower)")
    print("   • keyframes_per_segment: 6-8 (higher)")
    
    print("\\n🎯 FOR FEWER BUT BETTER KEYFRAMES:")
    print("   • base_quality_threshold: 0.18-0.25 (higher)")
    print("   • motion_threshold: 0.012-0.020 (higher)")
    print("   • max_summary_frames: 8-15 (lower)")
    print("   • frame_sampling_interval: 1.5-2.5 (higher)")
    print("   • keyframes_per_segment: 3-4 (lower)")
    
    print("\\n🎯 FOR BETTER EVENT DETECTION:")
    print("   • motion_threshold: 0.005-0.008 (lower)")
    print("   • burst_weight: 2.5-3.0 (higher)")
    print("   • event_importance_threshold: 0.20-0.25 (lower)")
    print("   • temporal_clustering_window: 15-25 (higher)")
    
    print("\\n🎯 FOR BETTER QUALITY:")
    print("   • enable_clahe: True")
    print("   • enable_denoising: True")
    print("   • compression_crf: 18-20 (lower)")
    print("   • output_resolution: '1080p'")
    
    print("\\n🎯 FOR FASTER PROCESSING:")
    print("   • compression_preset: 'ultrafast'")
    print("   • num_workers: 6-8 (higher)")
    print("   • keyframes_per_segment: 3-4 (lower)")
    print("   • enable_face_detection: False")

def main():
    """Run all examples"""
    
    print("🎬 VIDEO PROCESSING PIPELINE - QUICK START EXAMPLES")
    print("=" * 60)
    
    # Run examples
    process_single_video_example()
    
    # Uncomment the examples you want to run:
    
    # process_with_custom_config_example()
    # compare_configurations_example()
    
    # Always show parameter guide
    parameter_tuning_guide()
    
    print("\\n🎉 Examples complete! Check the output directories for results.")
    print("\\n📁 Default output structure:")
    print("   video_processing_outputs/")
    print("   ├── frames/              # Extracted keyframe images")
    print("   ├── compressed/          # Compressed videos")
    print("   ├── highlights/          # Highlight reel videos")
    print("   ├── reports/             # JSON reports and HTML gallery")
    print("   └── segments/            # Individual segment JSON files")

if __name__ == "__main__":
    main()