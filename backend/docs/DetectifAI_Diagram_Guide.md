# DetectifAI Diagram Creation Guide

## Overview
This guide provides detailed instructions for creating all required diagrams for the DetectifAI mid-evaluation report based on your system architecture and requirements.

## 1. Architecture Diagrams

### 1.1 High-Level Box and Line Diagram

**Purpose**: Show major system components and their relationships
**Tools**: Draw.io, Lucidchart, or TikZ in LaTeX

**Components to Include**:
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │  Mobile App     │    │  Admin Panel    │
│   (React/Next)  │    │   (Future)      │    │   (React)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
    ┌─────────────────────────────────────────────────────────┐
    │                API Gateway                              │
    │              (Flask Backend)                            │
    └─────────────────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Video Processing│    │ AI Detection    │    │ Event Processing│
│    Pipeline     │    │   Services      │    │     Engine      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
    ┌─────────────────────────────────────────────────────────┐
    │              Data Layer                                 │
    │  PostgreSQL | File Storage | Model Repository          │
    └─────────────────────────────────────────────────────────┘
```

### 1.2 Multi-tiered Architecture Diagram

**Layers to Show**:
1. **Presentation Tier**
   - Web Dashboard (React/Next.js)
   - Mobile Application (Future)
   - Admin Interface

2. **Application Tier**
   - Flask API Gateway
   - Authentication Service
   - Business Logic Controllers
   - User Management

3. **Processing Tier**
   - Video Processing Service
   - Object Detection Service (YOLOv11)
   - Facial Recognition Service
   - Event Aggregation Service
   - DetectifAI Event Processor

4. **Data Tier**
   - PostgreSQL Database
   - File Storage System
   - Model Repository
   - Cache Layer (Redis)

## 2. UML Diagrams

### 2.1 Use Case Diagram

**Primary Actors**:
- Security Officer
- Investigation Team
- Surveillance Supervisor
- System Administrator

**Key Use Cases**:
- Upload Video
- Monitor Live Feed
- Detect Suspicious Activity
- Generate Alert
- Search Historical Footage
- Export Report
- Manage Users
- Configure System

**Sample Structure**:
```
[Security Officer] ──→ (Monitor Live Feed)
                  ──→ (Respond to Alert)
                  ──→ (Export Incident Report)

[Investigation Team] ──→ (Search Historical Footage)
                    ──→ (Analyze Suspicious Activity)
                    ──→ (Generate Evidence Report)

[System Admin] ──→ (Manage Users)
              ──→ (Configure Detection Models)
              ──→ (Monitor System Performance)
```

### 2.2 Activity Diagram - Video Processing Workflow

**Main Flow**:
1. **Start**: Video Input Received
2. **Decision**: Live Stream or Recorded File?
3. **Process**: Video Preprocessing & Frame Extraction
4. **Process**: Object Detection Analysis
5. **Process**: Behavior Analysis
6. **Decision**: Suspicious Activity Detected?
7. **Process**: Generate Event & Alert
8. **Process**: Event Aggregation & Deduplication
9. **Process**: Store Results
10. **End**: Complete Processing

**Parallel Activities**:
- Facial Recognition Processing
- Motion Detection Analysis
- Quality Enhancement

### 2.3 Class Diagram - Core System Classes

**Main Classes**:

```python
class VideoProcessor:
    - video_path: string
    - config: VideoProcessingConfig
    + extract_keyframes()
    + enhance_frames()
    + segment_video()

class ObjectDetector:
    - fire_model: YOLOModel
    - weapon_model: YOLOModel
    + detect_objects()
    + annotate_frames()

class DetectifAIEvent:
    - event_id: string
    - event_type: DetectifAIEventType
    - threat_level: ThreatLevel
    - timestamp: datetime
    + assess_threat()
    + generate_description()

class EventAggregator:
    - similarity_threshold: float
    + deduplicate_events()
    + create_canonical_events()

class User:
    - user_id: string
    - role: UserRole
    - permissions: List[Permission]
    + authenticate()
    + authorize()

class SecurityAlert:
    - alert_id: string
    - event: DetectifAIEvent
    - recipients: List[User]
    + send_notification()
```

### 2.4 State Transition Diagram - Video Processing States

**States**:
1. **Idle**: System waiting for input
2. **Processing**: Video being analyzed
3. **Detecting**: AI models running
4. **Event_Generated**: Suspicious activity found
5. **Alert_Sent**: Notifications dispatched
6. **Completed**: Processing finished
7. **Error**: System error occurred

**Transitions**:
- Idle → Processing (on video upload)
- Processing → Detecting (frames extracted)
- Detecting → Event_Generated (suspicious activity found)
- Detecting → Completed (no suspicious activity)
- Event_Generated → Alert_Sent (notification required)
- Alert_Sent → Completed (processing finished)
- Any State → Error (on system error)
- Error → Idle (after error handling)

### 2.5 Sequence Diagram - Real-time Alert Scenario

**Actors**: User, Web Interface, API Gateway, Video Processor, Object Detector, Alert Service

**Flow**:
1. User uploads video to Web Interface
2. Web Interface sends request to API Gateway
3. API Gateway initializes Video Processor
4. Video Processor extracts keyframes
5. Video Processor calls Object Detector
6. Object Detector analyzes frames
7. Object Detector returns detection results
8. Video Processor generates DetectifAI events
9. Video Processor sends events to Alert Service
10. Alert Service sends notification to User
11. API Gateway returns processing results to Web Interface
12. Web Interface displays results to User

## 3. Data Flow Diagrams

### 3.1 Level 0 (Context Diagram)

**External Entities**:
- Security Personnel
- Camera Systems
- External APIs (Stripe, Notifications)
- Database Systems

**Single Process**: DetectifAI System

**Data Flows**:
- Video Streams → DetectifAI System
- User Commands → DetectifAI System
- DetectifAI System → Security Alerts
- DetectifAI System → Incident Reports
- DetectifAI System → System Statistics

### 3.2 Level 1 (Major Processes)

**Processes**:
1. **Video Input Processing**
   - Inputs: Raw video streams, user uploads
   - Outputs: Processed frames, metadata

2. **AI Analysis Engine**
   - Inputs: Processed frames
   - Outputs: Detection results, behavioral analysis

3. **Event Management**
   - Inputs: Detection results
   - Outputs: Aggregated events, alerts

4. **User Interface**
   - Inputs: User commands, system data
   - Outputs: Dashboards, reports

**Data Stores**:
- Video Storage
- Event Database
- User Database
- Model Repository

### 3.3 Level 2 (Detailed AI Analysis)

**Sub-processes**:
1. **Object Detection**
   - Fire Detection Model
   - Weapon Detection Model
   - Person Detection

2. **Behavior Analysis**
   - Motion Analysis
   - Action Recognition
   - Threat Assessment

3. **Event Generation**
   - Event Classification
   - Confidence Scoring
   - Metadata Extraction

## 4. Component Diagram

**Major Components**:

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Dashboard   │  │ Admin Panel │  │ Mobile App  │     │
│  │ Component   │  │ Component   │  │ Component   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                              |
┌─────────────────────────────────────────────────────────┐
│                 API Gateway Layer                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Auth        │  │ Video API   │  │ User API    │     │
│  │ Service     │  │ Service     │  │ Service     │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                              |
┌─────────────────────────────────────────────────────────┐
│                Processing Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Video       │  │ Object      │  │ Event       │     │
│  │ Processor   │  │ Detector    │  │ Aggregator  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                              |
┌─────────────────────────────────────────────────────────┐
│                   Data Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ PostgreSQL  │  │ File        │  │ Model       │     │
│  │ Database    │  │ Storage     │  │ Repository  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

## 5. Deployment Diagram

**Deployment Environments**:

### Development Environment
- Developer Workstation
- Local PostgreSQL
- Local File Storage
- GPU Development Server

### Testing Environment
- Test Server (Cloud VM)
- Test Database
- Mock External Services
- Load Testing Tools

### Production Environment
- Web Server Cluster
- Database Cluster (Master/Slave)
- File Storage Service (AWS S3/Azure Blob)
- GPU Processing Nodes
- Load Balancer
- Monitoring Services

## 6. Tools and Software for Diagram Creation

### 6.1 Online Tools
- **Draw.io (diagrams.net)**: Free, comprehensive diagramming
- **Lucidchart**: Professional diagramming with collaboration
- **Miro**: Collaborative whiteboarding and diagramming
- **PlantUML**: Text-based UML diagram generation

### 6.2 Desktop Software
- **Microsoft Visio**: Professional diagramming suite
- **OmniGraffle** (macOS): Advanced diagramming tool
- **StarUML**: UML modeling tool

### 6.3 LaTeX Integration
- **TikZ**: Native LaTeX drawing package
- **PGF/TikZ**: Advanced graphics for LaTeX
- **tikz-uml**: UML diagrams in LaTeX

## 7. Diagram Quality Guidelines

### 7.1 General Principles
- **Clarity**: Ensure all text is readable and diagrams are not cluttered
- **Consistency**: Use consistent symbols, colors, and naming conventions
- **Completeness**: Include all relevant components and relationships
- **Accuracy**: Ensure diagrams match actual system implementation

### 7.2 Technical Standards
- **Resolution**: Minimum 300 DPI for printed documents
- **Format**: Vector formats (SVG, PDF) preferred over raster (PNG, JPG)
- **Colors**: Use colorblind-friendly palettes
- **Labels**: Clear, descriptive labels for all components

### 7.3 Documentation Standards
- **Legends**: Include legends for symbols and colors used
- **Annotations**: Add explanatory notes where necessary
- **References**: Cross-reference diagrams with requirement numbers
- **Versions**: Maintain version control for diagram updates

## 8. Integration with LaTeX Document

### 8.1 Including Graphics
```latex
\usepackage{graphicx}
\usepackage{tikz}

% For external images
\begin{figure}[h!]
\centering
\includegraphics[width=0.8\textwidth]{architecture_diagram.pdf}
\caption{DetectifAI System Architecture}
\label{fig:architecture}
\end{figure}

% For TikZ diagrams
\begin{figure}[h!]
\centering
\begin{tikzpicture}
% TikZ code here
\end{tikzpicture}
\caption{Use Case Diagram}
\label{fig:usecase}
\end{figure}
```

### 8.2 Cross-referencing
```latex
As shown in Figure \ref{fig:architecture}, the system follows a multi-tiered architecture...
The use case diagram (Figure \ref{fig:usecase}) illustrates the primary interactions...
```

This comprehensive guide provides all the necessary information to create professional diagrams for your DetectifAI mid-evaluation report. Each diagram type serves a specific purpose in documenting your system's design and requirements.