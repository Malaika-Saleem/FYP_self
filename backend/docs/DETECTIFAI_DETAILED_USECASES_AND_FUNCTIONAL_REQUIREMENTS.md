# DetectifAI - Detailed Use Cases and Functional Requirements

## 2.1 Detailed Use Cases

### 2.1.1 Video Processing Use Cases

#### 1. Upload Video for Analysis
- **Actor**: Security Officer, Investigation Team, System Administrator
- **Purpose**: To upload video footage for comprehensive security analysis and threat detection.
- **Overview**: User uploads video files through the web dashboard for automated processing including object detection, event analysis, and report generation.
- **Precondition**: User has access to DetectifAI dashboard and video file is in supported format (.avi, .mp4, .mov, .mkv).
- **Postcondition**: Video is uploaded, processed through the complete pipeline, and results are available for review.
- **Main Flow**:
  (a) User accesses the DetectifAI dashboard at localhost:3001/dashboard.
  (b) User clicks "Upload Videos" button in the Video Footage widget.
  (c) System displays upload modal with drag-and-drop interface.
  (d) User selects or drags video file into upload area.
  (e) System validates file format, size, and generates unique video ID.
  (f) User clicks "Upload Video for Fire Detection Analysis" to initiate processing.
  (g) System uploads file to backend/uploads/ directory and starts processing pipeline.
  (h) System displays real-time processing status with progress indicators.
  (i) System automatically redirects to results page upon completion.
- **Alternative Flow**:
  (a) If file format is unsupported, system displays error message and suggests supported formats.
  (b) If file exceeds size limit, system shows compression recommendations.
  (c) If processing gets stuck, system provides "Check Results Manually" button for direct navigation.

#### 2. Monitor Video Processing Status
- **Actor**: Security Officer, Investigation Team
- **Purpose**: To track real-time progress of video processing pipeline and receive updates.
- **Overview**: System provides continuous status updates during video processing with automatic redirection upon completion.
- **Precondition**: Video has been uploaded and processing initiated.
- **Postcondition**: User is informed of processing completion and can access results.
- **Main Flow**:
  (a) System displays initial processing status (10% - Upload Complete).
  (b) System polls /api/status/{videoId} every 2 seconds for updates.
  (c) System updates progress indicator showing current stage (Keyframes: 30%, Detection: 60%, Compression: 90%).
  (d) System displays estimated completion time when available.
  (e) System automatically redirects to results page when processing reaches 100%.
- **Alternative Flow**:
  (a) If processing appears stuck, system displays manual navigation option.
  (b) If API polling fails, system retries with exponential backoff and shows connection status.
  (c) If server restart occurs, system uses disk-based recovery to reconstruct processing status.

#### 3. Extract and Enhance Video Keyframes
- **Actor**: System (OptimizedVideoProcessor)
- **Purpose**: To extract representative frames from video for analysis while maintaining quality.
- **Overview**: System automatically extracts keyframes at optimal intervals and enhances quality for accurate object detection.
- **Precondition**: Video file uploaded and accessible in uploads/ directory.
- **Postcondition**: Keyframes extracted, enhanced, and saved with metadata for object detection pipeline.
- **Main Flow**:
  (a) System loads video file using OpenCV and analyzes properties (duration, FPS, resolution).
  (b) System calculates temporal sampling rate (~1 frame per second for optimal coverage).
  (c) System extracts keyframes based on temporal sampling strategy.
  (d) System evaluates frame quality metrics and applies CLAHE enhancement to low-quality frames.
  (e) System saves keyframes to video_processing_outputs/{videoId}/frames/ directory.
  (f) System generates frame metadata with precise timestamps.
  (g) System updates processing status to indicate keyframe extraction completion.
- **Alternative Flow**:
  (a) If video corruption detected, system skips corrupted frames and continues with available frames.
  (b) If insufficient disk space, system cleans temporary files and reduces frame quality if needed.

### 2.1.2 Object Detection Use Cases

#### 4. Detect Objects in Video Frames
- **Actor**: System (ObjectDetectionIntegrator), YOLO Models
- **Purpose**: To identify fire, weapons, and other security threats in extracted keyframes using AI models.
- **Overview**: System runs YOLO object detection models on keyframes to identify potential security threats with confidence scoring.
- **Precondition**: Keyframes extracted and YOLO models loaded (fire_yolo11.pt, yolov11_knife_gun.pt).
- **Postcondition**: Objects detected, annotated frames created, and detection metadata generated for event processing.
- **Main Flow**:
  (a) System loads fire detection model and weapon detection model.
  (b) System processes each keyframe through both detection models.
  (c) System filters detections by confidence threshold (>0.5) to reduce false positives.
  (d) System extracts bounding box coordinates, class labels, and confidence scores.
  (e) System creates annotated versions of frames with detection overlays.
  (f) System saves detection_metadata.json with comprehensive results.
  (g) System calculates detection statistics for reporting.
- **Alternative Flow**:
  (a) If no objects detected, system creates empty detection metadata and continues processing.
  (b) If model loading fails, system logs error and attempts reload or falls back to basic processing.

#### 5. Create Security Events from Detections
- **Actor**: System (ObjectDetectionIntegrator)
- **Purpose**: To convert object detections into structured security events for analysis and response.
- **Overview**: System analyzes detection patterns and creates time-based security events with appropriate priority levels.
- **Precondition**: Object detection completed with metadata available.
- **Postcondition**: Security events created and ready for DetectifAI framework processing.
- **Main Flow**:
  (a) System analyzes detection results by timestamp and object type.
  (b) System groups consecutive detections of same object class into events.
  (c) System determines event start/end timestamps and calculates average confidence.
  (d) System assigns unique event ID and sets priority based on object type.
  (e) System creates structured event data with keyframe references.
  (f) System adds events to aggregation pipeline for deduplication.
- **Alternative Flow**:
  (a) For single frame detections, system creates short-duration events with minimum visibility window.
  (b) For multiple concurrent object types, system creates separate events maintaining temporal relationships.

### 2.1.3 Event Processing Use Cases

#### 6. Process DetectifAI Security Framework Events
- **Actor**: System (DetectifAIEventProcessor)
- **Purpose**: To convert detection events into DetectifAI security framework format for standardized processing.
- **Overview**: System maps object detection events to security event types with appropriate threat levels and response protocols.
- **Precondition**: Object-based events created and DetectifAI event processor initialized.
- **Postcondition**: Security events formatted for DetectifAI framework with threat classifications.
- **Main Flow**:
  (a) System receives object-based events from detection pipeline.
  (b) System maps detection events to security event types (fire, weapon, suspicious activity).
  (c) System determines threat level based on object type and detection confidence.
  (d) System assigns investigation priority on 1-10 scale.
  (e) System sets immediate response flags for high-priority events.
  (f) System creates DetectifAI-compatible event structure with security metadata.
  (g) System prepares events for dashboard display and reporting.
- **Alternative Flow**:
  (a) For high-threat events (weapons, fire), system flags for immediate response and escalates priority.
  (b) For multiple concurrent events, system correlates related events and creates composite assessment.

#### 7. Aggregate and Deduplicate Events
- **Actor**: System (EventDeduplicationEngine)
- **Purpose**: To eliminate redundant events and create clean timeline for efficient review.
- **Overview**: System identifies similar events within time windows and merges them into canonical representations.
- **Precondition**: Multiple events generated with temporal and spatial metadata.
- **Postcondition**: Deduplicated event timeline with reduced redundancy and preserved audit trail.
- **Main Flow**:
  (a) System analyzes temporal proximity of events (within 3-second window).
  (b) System compares event types, locations, and confidence levels for similarity.
  (c) System identifies duplicate or highly similar events using similarity thresholds.
  (d) System merges related events preserving highest confidence and most complete metadata.
  (e) System creates deduplicated timeline maintaining source event references.
  (f) System generates final event summary optimized for user review.
- **Alternative Flow**:
  (a) If no duplicates found, system passes all events through unchanged.
  (b) For complex overlaps, system applies weighted merging preserving distinct characteristics.

### 2.1.4 Dashboard and User Interface Use Cases

#### 8. View Video Analysis Results
- **Actor**: Security Officer, Investigation Team, System Administrator
- **Purpose**: To review comprehensive analysis results including detected objects, events, and video playback.
- **Overview**: Users access detailed results page with video player, detection summary, keyframe gallery, and event timeline.
- **Precondition**: Video processing completed and results available in backend storage.
- **Postcondition**: User has comprehensive view of analysis results and can take appropriate action.
- **Main Flow**:
  (a) User accesses results page via automatic redirect or manual navigation to /results/{videoId}.
  (b) System loads and displays compressed video player with standard playback controls.
  (c) System presents processing statistics (keyframes extracted, objects detected, processing time).
  (d) System shows keyframe gallery with filtering options (All Keyframes, Detection Only).
  (e) System displays detection details with object types, confidence scores, and timestamps.
  (f) System provides event timeline with security classifications and priority levels.
  (g) System offers download options for reports, metadata, and original video access.
- **Alternative Flow**:
  (a) If no detections found, system displays "No suspicious activity detected" with option for manual review.
  (b) For large detection counts, system implements pagination and filtering in keyframe gallery.

#### 9. Filter and Browse Detection Results
- **Actor**: Security Officer, Investigation Team
- **Purpose**: To efficiently navigate through detected objects and focus on relevant security events.
- **Overview**: Users can filter keyframes and detections by type, confidence, and timestamp for targeted investigation.
- **Precondition**: Analysis results available with detection metadata.
- **Postcondition**: User can efficiently locate and investigate specific types of security events.
- **Main Flow**:
  (a) User accesses keyframe gallery in results page.
  (b) System displays filtering options (All Keyframes, Detection Only, By Object Type, By Confidence).
  (c) User selects filter criteria to focus on specific detection types.
  (d) System updates gallery display showing only matching keyframes with detection highlights.
  (e) User clicks on keyframes to view detailed detection information with bounding boxes.
  (f) System provides navigation controls for efficient browsing between filtered results.
- **Alternative Flow**:
  (a) If no detections match filter criteria, system displays appropriate message and suggests alternative filters.
  (b) For timestamp-based navigation, system provides chronological controls and timeline scrubbing.

### 2.1.5 System Administration Use Cases

#### 10. Manage Video Processing Pipeline
- **Actor**: System Administrator, Development Team
- **Purpose**: To monitor system performance, manage processing queue, and troubleshoot issues.
- **Overview**: Administrators access system monitoring tools to ensure optimal performance and resolve processing issues.
- **Precondition**: Administrative access granted and system monitoring tools available.
- **Postcondition**: System performance optimized and issues resolved or escalated appropriately.
- **Main Flow**:
  (a) Administrator accesses system monitoring dashboard with processing queue status.
  (b) System displays current jobs, processing times, and resource utilization metrics.
  (c) Administrator reviews performance statistics and identifies potential bottlenecks.
  (d) System provides options to restart failed jobs or adjust processing parameters.
  (e) Administrator can reload models, adjust thresholds, or modify system configuration.
  (f) System logs all administrative actions for audit and debugging purposes.
- **Alternative Flow**:
  (a) If system overload detected, administrator can throttle processing queue and prioritize critical jobs.
  (b) For processing failures, system provides detailed error logs and automatic recovery options.

#### 11. Handle System Errors and Recovery
- **Actor**: System, Administrator
- **Purpose**: To gracefully handle processing failures and maintain system stability.
- **Overview**: System detects errors, attempts automatic recovery, and provides fallback mechanisms to preserve data integrity.
- **Precondition**: Processing pipeline active and error detection systems enabled.
- **Postcondition**: System remains stable with errors resolved or gracefully degraded functionality.
- **Main Flow**:
  (a) System detects failure in pipeline component and logs detailed error information.
  (b) System attempts automatic recovery using fallback methods (e.g., OpenCV if FFmpeg fails).
  (c) System isolates failed components to prevent cascade failures.
  (d) System continues processing with remaining functional components.
  (e) System marks processing as "completed with warnings" and notifies users of limitations.
  (f) System generates diagnostic reports for administrator review.
- **Alternative Flow**:
  (a) For critical failures, system halts processing to prevent data corruption and saves partial results.
  (b) For recoverable errors, system retries with modified parameters and continues normal operation.

### 2.1.6 API and Integration Use Cases

#### 12. Process API Requests
- **Actor**: Frontend Application, External Systems
- **Purpose**: To handle RESTful API requests for video upload, status checking, and result retrieval.
- **Overview**: Flask backend processes HTTP requests with proper authentication, validation, and error handling.
- **Precondition**: Flask server running with configured endpoints and CORS settings.
- **Postcondition**: Client receives appropriate response with correct status and data format.
- **Main Flow**:
  (a) Client sends HTTP request to Flask API endpoint with required parameters.
  (b) System validates request format, authentication, and parameter completeness.
  (c) System routes request to appropriate handler function for processing.
  (d) System executes business logic and formats response data as JSON.
  (e) System returns response with appropriate HTTP status codes and CORS headers.
  (f) System logs request/response details for monitoring and debugging.
- **Alternative Flow**:
  (a) For invalid requests, system returns 400 Bad Request with detailed error information.
  (b) For missing resources, system returns 404 Not Found with alternative suggestions.
  (c) For server errors, system returns 500 Internal Server Error while maintaining system stability.

### 2.1.7 Performance and Quality Assurance Use Cases

#### 13. Monitor System Performance
- **Actor**: System, Performance Monitor
- **Purpose**: To ensure optimal processing performance and maintain quality standards.
- **Overview**: System continuously monitors processing times, resource utilization, and detection accuracy for optimization.
- **Precondition**: Performance monitoring enabled with configured metrics and thresholds.
- **Postcondition**: System performance maintained within acceptable parameters with optimization recommendations.
- **Main Flow**:
  (a) System tracks processing time for each pipeline stage and overall throughput.
  (b) System monitors resource utilization (CPU, memory, disk I/O) and detection accuracy.
  (c) System calculates performance metrics (frames per second, detection confidence averages).
  (d) System identifies bottlenecks and provides optimization recommendations.
  (e) System adjusts processing parameters dynamically for optimal performance.
  (f) System generates performance reports for capacity planning and system improvement.
- **Alternative Flow**:
  (a) If performance degradation detected, system adjusts quality settings to maintain throughput.
  (b) For resource exhaustion, system throttles processing and performs cleanup operations.

#### 14. Recover Processing Status from Disk
- **Actor**: System
- **Purpose**: To reconstruct processing status after system restart using disk-based evidence.
- **Overview**: System analyzes file system to determine processing completion status when in-memory data is lost.
- **Precondition**: Processing completed but server restarted, causing loss of in-memory status.
- **Postcondition**: Processing status accurately reconstructed allowing normal result access.
- **Main Flow**:
  (a) User attempts to access processing status for video with lost in-memory data.
  (b) System detects video ID not in memory but finds corresponding files on disk.
  (c) System scans video_processing_outputs/{videoId}/ directory for completion indicators.
  (d) System reconstructs status based on file existence (compressed video = completed).
  (e) System creates recovery status message and updates progress to 100%.
  (f) System provides normal results access despite initial memory loss.
- **Alternative Flow**:
  (a) For partial processing, system identifies completed stages and offers resumption options.
  (b) For corrupted files, system validates integrity and suggests reprocessing if needed.

#### 15. Generate and Export Reports
- **Actor**: Security Officer, Investigation Team, System Administrator
- **Purpose**: To create comprehensive reports of video analysis results for documentation and sharing.
- **Overview**: System generates detailed reports including detection summaries, event timelines, and statistical analysis.
- **Precondition**: Video analysis completed with results and metadata available.
- **Postcondition**: Comprehensive reports generated in multiple formats for various use cases.
- **Main Flow**:
  (a) User accesses report generation options from results page.
  (b) System compiles detection statistics, event summaries, and processing metadata.
  (c) System generates report in requested format (PDF, JSON, CSV) with visual summaries.
  (d) System includes keyframe thumbnails, detection overlays, and confidence metrics.
  (e) System provides download options and temporary storage for generated reports.
  (f) System logs report generation for audit and usage tracking.
- **Alternative Flow**:
  (a) For custom reports, system allows filtering by detection type, confidence, or time range.
  (b) For large datasets, system provides paginated reports or summary-only options.

---

## 2.2 Functional Requirements

### 2.2.1 Module 1: Live Video Input & Preprocessing

1. **FR001**: The system shall accept video uploads in multiple formats including .avi, .mp4, .mov, and .mkv with file size limits up to 100MB (configurable).

2. **FR002**: Upon successful video upload, the system shall display a confirmation message and generate a unique video ID in format: video_YYYYMMDD_HHMMSS_hash.

3. **FR003**: The system shall automatically extract keyframes from uploaded videos at approximately 1 frame per second sampling rate.

4. **FR004**: The system shall apply CLAHE enhancement to low-quality keyframes to improve detection accuracy.

5. **FR005**: The system shall save extracted keyframes to organized directory structure: video_processing_outputs/{videoId}/frames/.

6. **FR006**: The system shall generate frame metadata including precise timestamps and quality metrics for each extracted keyframe.

7. **FR007**: The system shall provide real-time progress updates during keyframe extraction with percentage completion indicators.

8. **FR008**: The system shall handle video corruption gracefully by skipping corrupted frames and continuing with available content.

### 2.2.2 Module 2: Object Detection

9. **FR009**: The system shall load and utilize YOLO models for fire detection (fire_yolo11.pt) and weapon detection (yolov11_knife_gun.pt).

10. **FR010**: The system shall process each extracted keyframe through both detection models with configurable confidence thresholds (default >0.5).

11. **FR011**: The system shall extract bounding box coordinates, object class labels, and confidence scores for each detection.

12. **FR012**: The system shall create annotated versions of keyframes with detection overlays showing bounding boxes and labels.

13. **FR013**: The system shall generate detection_metadata.json containing comprehensive detection results and statistics.

14. **FR014**: The system shall achieve detection accuracy of >85% for fire events and >75% for weapon detection based on testing benchmarks.

15. **FR015**: The system shall process keyframes at 0.2-0.4 seconds per frame depending on system resources.

16. **FR016**: The system shall maintain false positive rates below 10% for weapon detection through confidence threshold optimization.

### 2.2.3 Module 3: Vision-Language Behavior Analysis & Captioning

17. **FR017**: The system shall analyze detection patterns to identify suspicious behaviors including weapon carrying, wall jumping, and violent activities.

18. **FR018**: The system shall generate natural language descriptions of detected events with timestamp information.

19. **FR019**: The system shall create time-stamped captions summarizing significant security incidents for each video.

20. **FR020**: The system shall correlate multiple detection types to identify complex security scenarios.

### 2.2.4 Module 4: Event Aggregation & De-duplication

21. **FR021**: The system shall group consecutive detections of the same object class within 3-second time windows into single events.

22. **FR022**: The system shall eliminate duplicate detections based on temporal proximity and spatial overlap (>70% bounding box overlap).

23. **FR023**: The system shall merge related events preserving highest confidence scores and most complete metadata.

24. **FR024**: The system shall reduce event redundancy by 20-40% through deduplication while maintaining audit trail of source events.

25. **FR025**: The system shall create canonical event representations with unique identifiers and priority classifications.

### 2.2.5 Module 5: Natural Language-Based Clip Retrieval

26. **FR026**: The system shall enable users to search video content using natural language queries matching event descriptions.

27. **FR027**: The system shall return relevant video clips with timestamps and contextual metadata based on search queries.

28. **FR028**: The system shall maintain searchable database of event descriptions and associated video segments.

### 2.2.6 Module 6: Facial Recognition & Image Search

29. **FR029**: The system shall capture and store facial data from individuals detected in suspicious events.

30. **FR030**: The system shall automatically recognize flagged individuals when they reappear in future footage.

31. **FR031**: The system shall allow users to upload photos to search for specific individuals across all recorded videos.

32. **FR032**: The system shall provide timestamps and event details for all appearances of searched individuals.

### 2.2.7 Module 7: Real-Time Monitoring Dashboard (Web Application)

33. **FR033**: The system shall provide a centralized web dashboard at localhost:3001/dashboard for monitoring video processing and results.

34. **FR034**: The system shall display real-time processing status with progress indicators updating every 2 seconds via /api/status/{videoId}.

35. **FR035**: The system shall automatically redirect users to results page upon processing completion (100% status).

36. **FR036**: The system shall provide manual navigation option ("Check Results Manually") when processing appears stuck.

37. **FR037**: The system shall display comprehensive results including video player, keyframe gallery, detection details, and event timeline.

38. **FR038**: The system shall offer filtering options for keyframes (All Keyframes, Detection Only, By Object Type, By Confidence).

39. **FR039**: The system shall provide downloadable reports in multiple formats (JSON, PDF) with processing summaries and detection statistics.

40. **FR040**: The system shall maintain responsive design supporting various screen sizes and devices.

### 2.2.8 Module 8: User Management Module

41. **FR041**: The system shall provide secure user authentication and session management for dashboard access.

42. **FR042**: The system shall implement role-based access control distinguishing between security officers, investigators, and administrators.

43. **FR043**: The system shall allow users to view their processing history and manage their uploaded videos.

44. **FR044**: The system shall provide user profile management with credential updates and notification preferences.

### 2.2.9 Module 9: Admin Module (CRUD Operations)

45. **FR045**: Authorized administrators shall be able to view system performance metrics including processing queue status and resource utilization.

46. **FR046**: Administrators shall be able to restart failed processing jobs and adjust system configuration parameters.

47. **FR047**: Administrators shall be able to reload detection models without full system restart.

48. **FR048**: Administrators shall be able to manage user accounts including creation, updates, and deletion.

49. **FR049**: The system shall provide comprehensive logging of all administrative actions for audit purposes.

50. **FR050**: Administrators shall be able to export system logs and diagnostic information for troubleshooting.

### 2.2.10 Module 10: Payment Module

51. **FR051**: The system shall integrate Stripe payment processing for subscription-based access to advanced features.

52. **FR052**: The system shall support multiple payment methods including credit cards and digital wallets.

53. **FR053**: The system shall provide secure transaction processing with PCI compliance standards.

54. **FR054**: The system shall generate payment receipts and manage subscription billing cycles.

## 2.3 Additional System Requirements

### 2.3.1 Performance Requirements

55. **FR055**: The system shall process 16-second videos in under 20 seconds on standard hardware configurations.

56. **FR056**: The system shall maintain API response times under 200ms for status checks and under 2 seconds for result retrieval.

57. **FR057**: The system shall support concurrent processing of multiple videos with queue management and resource allocation.

### 2.3.2 Error Handling and Recovery

58. **FR058**: The system shall implement graceful error handling with automatic fallback mechanisms (OpenCV when FFmpeg unavailable).

59. **FR059**: The system shall provide disk-based status recovery allowing result access after system restarts.

60. **FR060**: The system shall maintain data integrity during component failures and provide partial results when possible.

### 2.3.3 Security and Data Management

61. **FR061**: The system shall implement secure file storage with organized directory structures and access controls.

62. **FR062**: The system shall provide data retention policies with automatic cleanup of temporary files and old processing results.

63. **FR063**: The system shall maintain audit logs of all user actions and system events for security and compliance purposes.

### 2.3.4 Integration and Extensibility

64. **FR064**: The system shall provide RESTful API endpoints enabling integration with external security systems and applications.

65. **FR065**: The system shall support model updates and configuration changes without requiring system downtime.

66. **FR066**: The system shall maintain backward compatibility with existing video processing results and metadata formats.
