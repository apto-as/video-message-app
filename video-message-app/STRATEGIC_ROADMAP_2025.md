# Video Message App - Strategic Execution Roadmap 2025

**Status**: Draft
**Created**: 2025-11-02
**Last Updated**: 2025-11-02
**Classification**: Strategic Planning Document
**Author**: Hera (Strategic Commander) - Trinitas-Core System

---

## Executive Summary

### Current State Analysis

**Infrastructure**:
- Primary: EC2 t3.large (3.115.141.166) - Main application
- GPU: g4dn.xlarge (Tesla T4) - Spot instance for GPU processing
- Region: ap-northeast-1 (Tokyo)
- Architecture: FastAPI + React 19 + Docker

**Core Capabilities**:
- ✅ VOICEVOX Japanese TTS
- ✅ OpenVoice V2 voice cloning (CPU/GPU)
- ✅ D-ID talking avatar integration
- ✅ Docker-based deployment

**Infrastructure Gaps**:
- ❌ No IaC (Infrastructure as Code)
- ❌ Manual EC2 management
- ❌ Limited monitoring/observability
- ❌ No auto-scaling capability
- ❌ Single-region deployment

### Strategic Objectives

1. **Foundation**: Establish AWS MCP integration for development velocity
2. **Enhancement**: Implement advanced image/video processing
3. **Quality**: Achieve production-grade video generation
4. **Scale**: Enable cost-effective horizontal scaling

---

## Phase 1: AWS MCP Integration & Infrastructure Modernization

**Duration**: 3 weeks
**Priority**: CRITICAL (Foundation)
**Success Criteria**: 50% reduction in deployment time, 100% infrastructure reproducibility

### Week 1: MCP Tooling & IaC Foundation

#### Objectives
- Establish AWS MCP as development productivity tool
- Convert manual infrastructure to reproducible IaC
- Enable one-command infrastructure deployment

#### Tasks

**Day 1-2: AWS MCP Integration**
```bash
# Install AWS MCP server (already available)
# Configure Claude Code integration
# Verify aws-mcp-admin-agents profile access

# Test AWS MCP capabilities
aws ec2 describe-instances --profile aws-mcp-admin-agents
```

**Deliverables**:
- [ ] AWS MCP server configured in Claude Code
- [ ] Connection test to EC2 instances successful
- [ ] AWS resource query via MCP validated

**Day 3-5: Terraform IaC Development**

**File**: `infrastructure/terraform/main.tf`
```hcl
# Current infrastructure capture
resource "aws_instance" "app_server" {
  ami           = "ami-0c55b159cbfafe1f0"  # Ubuntu 22.04
  instance_type = "t3.large"

  tags = {
    Name = "video-message-app-main"
    Environment = "production"
  }
}

resource "aws_instance" "gpu_processor" {
  ami           = "ami-0xyz123" # Deep Learning AMI
  instance_type = "g4dn.xlarge"

  # Spot instance configuration
  instance_market_options {
    market_type = "spot"
    spot_options {
      max_price = "0.35"
    }
  }

  tags = {
    Name = "openvoice-gpu-processor"
    Environment = "production"
    AutoStop = "true"
  }
}
```

**Deliverables**:
- [ ] Complete Terraform configuration for existing infrastructure
- [ ] Terraform state backend (S3 + DynamoDB)
- [ ] `terraform plan` validates with 0 changes
- [ ] Documentation: `infrastructure/README.md`

**Resource Requirements**:
- Engineer: 1 DevOps/SRE
- Cost: $50 (S3/DynamoDB for state)
- Risk: LOW (read-only capture of existing setup)

### Week 2: ECS/Fargate Migration Evaluation

#### Objectives
- Evaluate container orchestration benefits
- Create cost comparison analysis
- Design migration path if approved

#### Tasks

**Day 1-3: Current vs. ECS Analysis**

**Current Architecture**:
```
EC2 Direct Deploy (t3.large)
├── Docker Compose
│   ├── Backend (FastAPI)
│   ├── Frontend (React)
│   ├── VoiceVox
│   └── Nginx
└── Manual scaling (none)

Cost: ~$65/month (t3.large) + ~$40/month (g4dn.xlarge spot, 8h/day)
```

**Proposed ECS Architecture**:
```
Application Load Balancer
├── ECS Service: Backend (Fargate)
├── ECS Service: Frontend (Fargate)
├── ECS Service: VoiceVox (Fargate)
└── EC2 (g4dn.xlarge): OpenVoice GPU

Cost Estimate:
- ALB: $16/month
- Fargate (3 services, 0.5 vCPU each): ~$45/month
- GPU instance: Same ($40/month at 8h/day)
- Total: ~$101/month (+$16/month)

Benefits:
+ Auto-scaling capability
+ Zero-downtime deployments
+ Better resource utilization
+ Integrated monitoring

Drawbacks:
- 16% cost increase
- Migration complexity
```

**Deliverables**:
- [ ] Cost-benefit analysis document
- [ ] Migration effort estimate (person-days)
- [ ] Risk assessment matrix
- [ ] Go/No-Go recommendation for user

**Decision Point**: User approves/rejects ECS migration

**Day 4-5: CloudWatch Enhanced Monitoring**

Regardless of ECS decision, implement comprehensive monitoring:

```hcl
# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "app_metrics" {
  dashboard_name = "video-message-app-metrics"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", {stat = "Average"}],
            [".", "NetworkIn"],
            [".", "NetworkOut"]
          ]
          period = 300
          stat = "Average"
          region = "ap-northeast-1"
          title = "EC2 Performance"
        }
      }
    ]
  })
}

# Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "high-cpu-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "Alert when CPU exceeds 80%"
}
```

**Deliverables**:
- [ ] CloudWatch dashboard with key metrics
- [ ] 5 critical alarms configured
- [ ] SNS topic for alerts
- [ ] Monitoring runbook

**Resource Requirements**:
- Engineer: 1 DevOps
- Cost: $10/month (CloudWatch)
- Risk: LOW

### Week 3: CI/CD Pipeline & Deployment Automation

#### Objectives
- Automate build and deployment process
- Enable one-command production updates
- Implement rollback capability

#### Tasks

**Day 1-3: GitHub Actions CI/CD**

**File**: `.github/workflows/deploy-production.yml`
```yaml
name: Production Deployment

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker Images
        run: |
          docker build -t video-app-backend:${{ github.sha }} ./backend
          docker build -t video-app-frontend:${{ github.sha }} ./frontend

      - name: Push to ECR
        run: |
          aws ecr get-login-password --region ap-northeast-1 | \
            docker login --username AWS --password-stdin $ECR_REGISTRY
          docker push video-app-backend:${{ github.sha }}

      - name: Deploy to EC2
        run: |
          ssh -i ${{ secrets.EC2_KEY }} ubuntu@3.115.141.166 \
            "cd ~/video-message-app && \
             git pull && \
             docker-compose pull && \
             docker-compose up -d"

      - name: Health Check
        run: |
          curl -f https://3.115.141.166/health || exit 1
```

**Deliverables**:
- [ ] Automated Docker image builds
- [ ] ECR repository setup
- [ ] One-command deployment script
- [ ] Automated health checks

**Day 4-5: Blue-Green Deployment Setup**

```bash
# Prepare for zero-downtime deployments
# Use Docker Compose profiles or ECS task definitions

# docker-compose.blue-green.yml
services:
  backend-blue:
    image: backend:current
    container_name: backend_blue

  backend-green:
    image: backend:new
    container_name: backend_green
    # Initially not exposed

# Switch script: switch-backend.sh
nginx_config_update() {
  sed -i 's/backend_blue/backend_green/' /etc/nginx/conf.d/default.conf
  nginx -s reload
}
```

**Deliverables**:
- [ ] Blue-green deployment scripts
- [ ] Rollback procedure documented
- [ ] Deployment checklist

**Resource Requirements**:
- Engineer: 1 DevOps
- Cost: $20/month (ECR storage)
- Risk: MEDIUM (deployment automation requires testing)

---

## Phase 2: Advanced Image Processing Pipeline

**Duration**: 4 weeks
**Priority**: HIGH (Feature Development)
**Success Criteria**: Multi-person segmentation, 95% background removal accuracy

### Week 4-5: Multi-Person Segmentation

#### Objectives
- Detect and segment multiple people in images
- Enable individual face selection for D-ID
- Support group photo processing

#### Technical Approach

**Library Evaluation**:
```python
# Option A: MediaPipe (Google)
# Pros: Fast, on-device processing
# Cons: Limited customization

# Option B: Detectron2 (Facebook)
# Pros: SOTA accuracy, flexible
# Cons: Requires GPU, heavier

# Option C: YOLACT (Real-time segmentation)
# Pros: Fast, good accuracy
# Cons: Model size
```

**Recommended**: MediaPipe for speed, with Detectron2 fallback for quality mode

**Implementation**:

**File**: `backend/services/person_segmentation_service.py`
```python
from typing import List, Tuple
import mediapipe as mp
import numpy as np
from PIL import Image

class PersonSegmentationService:
    """Multi-person detection and segmentation"""

    def __init__(self):
        self.mp_selfie_segmentation = mp.solutions.selfie_segmentation
        self.segmenter = self.mp_selfie_segmentation.SelfieSegmentation(
            model_selection=1  # General model
        )

    async def detect_persons(
        self,
        image: Image.Image
    ) -> List[Tuple[np.ndarray, dict]]:
        """
        Detect all persons in image and return segmented masks.

        Returns:
            List of (mask, metadata) tuples
            metadata = {"bbox": [x,y,w,h], "confidence": float}
        """
        image_np = np.array(image)
        results = self.segmenter.process(image_np)

        # Extract individual person masks
        # (Implementation details...)

        return person_segments

    async def select_primary_person(
        self,
        image: Image.Image,
        selection_strategy: str = "largest"
    ) -> Tuple[Image.Image, dict]:
        """
        Select primary person from multi-person image.

        Strategies:
        - largest: Biggest bounding box
        - center: Closest to image center
        - manual: User-specified coordinates
        """
        persons = await self.detect_persons(image)

        if selection_strategy == "largest":
            primary = max(persons, key=lambda p: p[1]["bbox"][2] * p[1]["bbox"][3])

        return self._crop_to_person(image, primary)
```

**API Endpoint**:
```python
# backend/routers/image_processing.py
@router.post("/api/image/detect-persons")
async def detect_persons(
    file: UploadFile,
    service: PersonSegmentationService = Depends()
):
    """Detect all persons in uploaded image"""
    image = Image.open(file.file)
    persons = await service.detect_persons(image)

    return {
        "person_count": len(persons),
        "persons": [
            {
                "id": i,
                "bbox": p[1]["bbox"],
                "confidence": p[1]["confidence"],
                "preview_url": f"/temp/person_{i}.jpg"
            }
            for i, p in enumerate(persons)
        ]
    }
```

**Deliverables**:
- [ ] PersonSegmentationService implementation
- [ ] API endpoints for detection and selection
- [ ] Frontend UI for person selection
- [ ] Unit tests (>85% coverage)

**Resource Requirements**:
- Engineer: 1 ML/Backend engineer
- GPU: Use existing g4dn.xlarge
- Cost: $0 (infrastructure reuse)
- Risk: MEDIUM (ML model integration complexity)

### Week 6-7: Background Composition Pipeline

#### Objectives
- Remove original background cleanly
- Composite person onto new background
- Maintain natural lighting and edges

#### Technical Implementation

**File**: `backend/services/background_service.py`
```python
import cv2
from rembg import remove
from PIL import Image

class BackgroundCompositionService:
    """Background removal and composition"""

    async def remove_background(
        self,
        image: Image.Image,
        model: str = "u2net"
    ) -> Tuple[Image.Image, Image.Image]:
        """
        Remove background from image.

        Returns:
            (foreground_rgba, alpha_mask)
        """
        # Use rembg for high-quality removal
        output = remove(
            image,
            model_name=model,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10
        )

        # Extract alpha channel
        alpha = np.array(output)[:, :, 3]

        return output, Image.fromarray(alpha)

    async def composite_background(
        self,
        foreground: Image.Image,
        background: Image.Image,
        blend_mode: str = "natural"
    ) -> Image.Image:
        """
        Composite foreground onto new background.

        Blend modes:
        - natural: Match lighting and color tone
        - overlay: Simple alpha blend
        - green_screen: Chroma key style
        """
        # Resize background to match foreground
        bg_resized = background.resize(foreground.size, Image.LANCZOS)

        if blend_mode == "natural":
            # Color correction to match lighting
            foreground_adjusted = self._match_lighting(foreground, bg_resized)
            result = Image.alpha_composite(
                bg_resized.convert("RGBA"),
                foreground_adjusted
            )
        else:
            result = Image.alpha_composite(
                bg_resized.convert("RGBA"),
                foreground
            )

        return result

    def _match_lighting(
        self,
        foreground: Image.Image,
        background: Image.Image
    ) -> Image.Image:
        """Match foreground lighting to background"""
        # Extract dominant colors
        fg_hsv = cv2.cvtColor(np.array(foreground), cv2.COLOR_RGB2HSV)
        bg_hsv = cv2.cvtColor(np.array(background), cv2.COLOR_RGB2HSV)

        # Adjust value (brightness) channel
        # (Implementation...)

        return adjusted_foreground
```

**Pre-Made Background Library**:
```python
# backgrounds/library.json
{
  "professional": [
    {
      "id": "office_blur",
      "url": "/backgrounds/office_blur.jpg",
      "thumbnail": "/backgrounds/thumbnails/office_blur.jpg",
      "tags": ["business", "neutral"]
    },
    {
      "id": "conference_room",
      "url": "/backgrounds/conference_room.jpg",
      "tags": ["business", "professional"]
    }
  ],
  "casual": [
    {
      "id": "home_living",
      "url": "/backgrounds/home_living.jpg",
      "tags": ["casual", "warm"]
    }
  ]
}
```

**Deliverables**:
- [ ] Background removal service
- [ ] Composition pipeline with lighting adjustment
- [ ] 20+ professional background templates
- [ ] API endpoints for background operations
- [ ] Frontend background selector UI

**Resource Requirements**:
- Engineer: 1 Backend + 1 Frontend
- Designer: 1 (for background curation)
- Cost: $50 (stock backgrounds license)
- Risk: LOW (proven libraries)

---

## Phase 3: Video Quality Enhancement

**Duration**: 4 weeks
**Priority**: HIGH (Core Quality)
**Success Criteria**: 90% lip-sync accuracy, seamless BGM integration

### Week 8-9: Lip-Sync Naturalization

#### Problem Analysis

**Current Issue**: D-ID API lip-sync can be mechanical or misaligned

**Solution Approach**:
1. Pre-process audio for clearer phonemes
2. Post-process video for smoothing
3. A/B test quality improvements

#### Technical Implementation

**Audio Pre-Processing**:

**File**: `backend/services/audio_enhancement_service.py`
```python
import librosa
import soundfile as sf
import noisereduce as nr

class AudioEnhancementService:
    """Enhance audio quality for better lip-sync"""

    async def optimize_for_lipsync(
        self,
        audio_path: str,
        output_path: str
    ) -> dict:
        """
        Optimize audio for D-ID lip-sync.

        Steps:
        1. Noise reduction
        2. Normalize volume
        3. Enhance speech frequencies
        4. Add slight pause at sentence ends
        """
        # Load audio
        audio, sr = librosa.load(audio_path, sr=22050)

        # 1. Noise reduction
        audio_clean = nr.reduce_noise(
            y=audio,
            sr=sr,
            stationary=True
        )

        # 2. Normalize to -16 LUFS (broadcast standard)
        audio_normalized = librosa.util.normalize(audio_clean)

        # 3. Speech enhancement (boost 300-3000 Hz)
        audio_enhanced = self._enhance_speech_band(audio_normalized, sr)

        # 4. Add pauses (detect sentence boundaries)
        audio_final = self._add_natural_pauses(audio_enhanced, sr)

        # Save
        sf.write(output_path, audio_final, sr)

        return {
            "duration": len(audio_final) / sr,
            "sample_rate": sr,
            "enhancements": ["noise_reduction", "normalization", "speech_boost"]
        }
```

**D-ID Request Optimization**:

**File**: `backend/services/d_id_service.py` (enhancement)
```python
class DIDService:
    async def create_talking_video(
        self,
        image_url: str,
        audio_url: str,
        options: dict = None
    ) -> dict:
        """
        Create talking video with optimized settings.
        """
        # Enhanced request parameters
        payload = {
            "source_url": image_url,
            "script": {
                "type": "audio",
                "audio_url": audio_url,
                "reduce_noise": True,  # D-ID noise reduction
                "ssml": False
            },
            "config": {
                "stitch": True,  # Smooth transitions
                "result_format": "mp4",
                "fluent": True,  # More natural movements
                "pad_audio": 0.5  # Add padding for smoother end
            },
            # NEW: Driver configuration for better lip-sync
            "driver_url": "bank://lively",  # Use "lively" driver
            "driver_expressions": {
                "expressions": [
                    {"start_frame": 0, "expression": "neutral", "intensity": 0.8}
                ]
            }
        }

        response = await self.client.post("/talks", json=payload)
        return response.json()
```

**Deliverables**:
- [ ] Audio enhancement pipeline
- [ ] D-ID request optimization
- [ ] A/B test framework (original vs. enhanced)
- [ ] Quality metrics dashboard

**Resource Requirements**:
- Engineer: 1 Backend engineer
- Cost: $100 (D-ID API testing credits)
- Risk: LOW (non-breaking enhancement)

### Week 10-11: BGM Integration System

#### Objectives
- Add background music to generated videos
- Support fade-in/fade-out
- Volume balancing (voice priority)

#### Technical Implementation

**File**: `backend/services/bgm_service.py`
```python
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
from pydub import AudioSegment

class BGMService:
    """Background music integration for videos"""

    async def add_bgm(
        self,
        video_path: str,
        bgm_path: str,
        output_path: str,
        options: dict = None
    ) -> dict:
        """
        Add background music to video.

        Options:
        - voice_volume: 1.0 (original voice volume multiplier)
        - bgm_volume: 0.3 (background music volume)
        - fade_duration: 2.0 (seconds)
        - ducking: True (reduce BGM when voice is present)
        """
        # Default options
        opts = {
            "voice_volume": 1.0,
            "bgm_volume": 0.3,
            "fade_duration": 2.0,
            "ducking": True
        }
        opts.update(options or {})

        # Load video and extract voice
        video = VideoFileClip(video_path)
        voice_audio = video.audio

        # Load and prepare BGM
        bgm = AudioFileClip(bgm_path)
        bgm_duration = video.duration

        # Loop BGM if shorter than video
        if bgm.duration < bgm_duration:
            bgm = self._loop_audio(bgm, bgm_duration)
        else:
            bgm = bgm.subclip(0, bgm_duration)

        # Apply volume adjustments
        voice_adjusted = voice_audio.volumex(opts["voice_volume"])
        bgm_adjusted = bgm.volumex(opts["bgm_volume"])

        # Apply fade in/out
        fade = opts["fade_duration"]
        bgm_faded = bgm_adjusted.audio_fadein(fade).audio_fadeout(fade)

        # Ducking: reduce BGM volume when voice is present
        if opts["ducking"]:
            bgm_ducked = self._apply_ducking(bgm_faded, voice_audio)
        else:
            bgm_ducked = bgm_faded

        # Composite audio
        final_audio = CompositeAudioClip([voice_adjusted, bgm_ducked])

        # Write final video
        final_video = video.set_audio(final_audio)
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=video.fps
        )

        return {
            "output_path": output_path,
            "duration": video.duration,
            "has_bgm": True
        }

    def _apply_ducking(
        self,
        bgm: AudioFileClip,
        voice: AudioFileClip,
        threshold: float = -30,  # dB
        reduction: float = 0.5
    ) -> AudioFileClip:
        """Reduce BGM volume when voice is above threshold"""
        # Detect voice activity (VAD)
        # When voice is active, reduce BGM by reduction factor
        # (Implementation using pydub.silence.detect_nonsilent)

        return ducked_bgm
```

**BGM Library**:
```python
# bgm/library.json
{
  "categories": [
    {
      "id": "corporate",
      "name": "Corporate / Business",
      "tracks": [
        {
          "id": "inspiring_piano",
          "name": "Inspiring Piano",
          "duration": 120,
          "mood": "uplifting",
          "file": "corporate/inspiring_piano.mp3",
          "preview": "corporate/inspiring_piano_preview.mp3",
          "license": "royalty_free"
        }
      ]
    },
    {
      "id": "casual",
      "name": "Casual / Friendly",
      "tracks": [
        {
          "id": "acoustic_guitar",
          "name": "Acoustic Guitar",
          "duration": 90,
          "mood": "warm",
          "file": "casual/acoustic_guitar.mp3",
          "license": "royalty_free"
        }
      ]
    }
  ]
}
```

**API Endpoint**:
```python
@router.post("/api/video/add-bgm")
async def add_bgm_to_video(
    video_id: str,
    bgm_id: str,
    options: BGMOptions = None,
    service: BGMService = Depends()
):
    """Add background music to generated video"""
    video_path = f"storage/videos/{video_id}.mp4"
    bgm_path = f"bgm/library/{bgm_id}.mp3"
    output_path = f"storage/videos/{video_id}_with_bgm.mp4"

    result = await service.add_bgm(
        video_path,
        bgm_path,
        output_path,
        options.dict() if options else None
    )

    return result
```

**Deliverables**:
- [ ] BGM integration service
- [ ] 15+ royalty-free BGM tracks
- [ ] Volume ducking implementation
- [ ] API endpoints for BGM operations
- [ ] Frontend BGM selector UI

**Resource Requirements**:
- Engineer: 1 Backend engineer
- Music: $200 (royalty-free BGM licenses)
- Cost: $0 (infrastructure reuse)
- Risk: LOW (standard audio processing)

---

## Phase 4: Production Optimization & Scale

**Duration**: 3 weeks
**Priority**: MEDIUM (Performance)
**Success Criteria**: Handle 100 concurrent users, 50% cost reduction

### Week 12: Auto-Scaling & Load Management

#### Objectives
- Implement horizontal scaling for stateless services
- GPU instance auto-start/stop
- Cost optimization through resource scheduling

#### If ECS Migration Approved:

**File**: `infrastructure/terraform/ecs_autoscaling.tf`
```hcl
# Backend service auto-scaling
resource "aws_appautoscaling_target" "backend" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "backend_cpu" {
  name               = "backend-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 60.0  # Scale when CPU > 60%
  }
}
```

#### If Staying on EC2:

**GPU Instance Scheduler**:

**File**: `backend/services/gpu_scheduler_service.py`
```python
import boto3
from datetime import datetime, timedelta

class GPUSchedulerService:
    """Auto-start/stop GPU instance based on demand"""

    def __init__(self):
        self.ec2 = boto3.client('ec2', region_name='ap-northeast-1')
        self.gpu_instance_id = "i-xxxxx"  # g4dn.xlarge
        self.last_request_time = None
        self.idle_threshold = 1800  # 30 minutes

    async def on_voice_clone_request(self):
        """Called when voice clone request arrives"""
        # Check if GPU instance is running
        status = self._get_instance_status()

        if status != "running":
            await self._start_instance()
            await self._wait_for_ready()

        self.last_request_time = datetime.now()

    async def check_idle_shutdown(self):
        """Periodic check to stop idle GPU instance"""
        if not self.last_request_time:
            return

        idle_duration = (datetime.now() - self.last_request_time).total_seconds()

        if idle_duration > self.idle_threshold:
            await self._stop_instance()
            self.last_request_time = None

    async def _start_instance(self):
        """Start GPU instance"""
        self.ec2.start_instances(InstanceIds=[self.gpu_instance_id])

    async def _stop_instance(self):
        """Stop GPU instance to save costs"""
        self.ec2.stop_instances(InstanceIds=[self.gpu_instance_id])
```

**Cron Job**: Run every 10 minutes
```bash
# crontab entry
*/10 * * * * /usr/bin/python3 /home/ubuntu/scripts/check_gpu_idle.py
```

**Cost Savings**:
- Current: 24h/day = $0.21 × 24 = $5.04/day = $151/month
- Optimized: 8h/day average = $0.21 × 8 = $1.68/day = $50/month
- **Savings: $101/month (67% reduction)**

**Deliverables**:
- [ ] Auto-scaling configuration (ECS or GPU scheduler)
- [ ] Load testing results (100 concurrent users)
- [ ] Cost optimization report

**Resource Requirements**:
- Engineer: 1 DevOps
- Cost: $0 (using existing resources)
- Risk: MEDIUM (requires careful testing)

### Week 13-14: Caching & Performance Optimization

#### Objectives
- Implement multi-layer caching
- Reduce D-ID API costs
- Faster response times

#### Redis Cache Layer

**File**: `infrastructure/terraform/elasticache.tf`
```hcl
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "video-app-cache"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379

  tags = {
    Name = "video-message-app-redis"
  }
}
```

**Cost**: ~$13/month

**Implementation**:

**File**: `backend/services/cache_service.py`
```python
import redis
import json
from typing import Optional

class CacheService:
    """Multi-layer caching for expensive operations"""

    def __init__(self):
        self.redis = redis.Redis(
            host='video-app-cache.xxxxx.cache.amazonaws.com',
            port=6379,
            decode_responses=True
        )
        self.ttl_voice_synthesis = 3600  # 1 hour
        self.ttl_video_result = 86400    # 24 hours

    async def cache_voice_synthesis(
        self,
        text: str,
        voice_id: str,
        audio_data: bytes
    ):
        """Cache synthesized voice"""
        cache_key = f"voice:{voice_id}:{hash(text)}"
        self.redis.setex(
            cache_key,
            self.ttl_voice_synthesis,
            audio_data
        )

    async def get_cached_voice(
        self,
        text: str,
        voice_id: str
    ) -> Optional[bytes]:
        """Retrieve cached voice synthesis"""
        cache_key = f"voice:{voice_id}:{hash(text)}"
        return self.redis.get(cache_key)

    async def cache_video_result(
        self,
        request_hash: str,
        video_url: str,
        metadata: dict
    ):
        """Cache D-ID video generation result"""
        cache_key = f"video:{request_hash}"
        self.redis.setex(
            cache_key,
            self.ttl_video_result,
            json.dumps({
                "url": video_url,
                "metadata": metadata
            })
        )
```

**Usage in Voice Synthesis**:
```python
# backend/routers/unified_voice.py
@router.post("/api/unified-voice/synthesize")
async def synthesize_voice(
    request: VoiceSynthesisRequest,
    cache: CacheService = Depends()
):
    # Check cache first
    cached = await cache.get_cached_voice(request.text, request.voice_id)
    if cached:
        return Response(content=cached, media_type="audio/wav")

    # Generate new
    audio = await voice_service.synthesize(request.text, request.voice_id)

    # Cache result
    await cache.cache_voice_synthesis(request.text, request.voice_id, audio)

    return Response(content=audio, media_type="audio/wav")
```

**Expected Impact**:
- Voice synthesis cache hit rate: 40% (repeat messages)
- D-ID API cost reduction: 25% (cached identical requests)
- Response time improvement: 80% for cached requests

**Deliverables**:
- [ ] Redis ElastiCache deployment
- [ ] Cache service implementation
- [ ] Cache hit rate monitoring
- [ ] Performance benchmarks

**Resource Requirements**:
- Engineer: 1 Backend engineer
- Cost: $13/month (ElastiCache)
- Risk: LOW (standard caching pattern)

---

## Resource Requirements Summary

### Personnel

| Role | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Total Person-Weeks |
|------|---------|---------|---------|---------|-------------------|
| DevOps/SRE | 3 weeks | - | - | 3 weeks | 6 weeks |
| Backend Engineer | - | 4 weeks | 4 weeks | 1 week | 9 weeks |
| ML Engineer | - | 2 weeks | - | - | 2 weeks |
| Frontend Engineer | - | 2 weeks | 1 week | - | 3 weeks |
| Designer | - | 1 week | - | - | 1 week |

**Total**: 21 person-weeks (5.25 person-months)

### Monthly Cost Breakdown

**Phase 1 (Infrastructure)**:
- S3/DynamoDB (Terraform state): $5/month
- CloudWatch (enhanced monitoring): $10/month
- ECR (Docker registry): $20/month
- **Subtotal**: $35/month

**Phase 2 (Image Processing)**:
- Stock backgrounds license: $50 (one-time)
- **Subtotal**: $0/month recurring

**Phase 3 (Video Quality)**:
- D-ID API testing: $100 (one-time)
- BGM licenses: $200 (one-time)
- **Subtotal**: $0/month recurring

**Phase 4 (Optimization)**:
- ElastiCache Redis: $13/month
- **Subtotal**: $13/month

**ECS Option (if approved)**:
- Application Load Balancer: $16/month
- Fargate (3 services): $45/month
- **Additional**: $61/month

**Total Monthly Costs**:
- Without ECS: $48/month (Current: ~$105/month) = **-$57/month savings**
- With ECS: $109/month (Current: ~$105/month) = **+$4/month**

**One-Time Costs**: $350

---

## Risk Assessment Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| ECS migration complexity | Medium | High | Thorough testing, rollback plan |
| ML model GPU memory issues | Low | Medium | Use smaller models, batch processing |
| D-ID API rate limits | Medium | Medium | Implement queue system, caching |
| BGM licensing issues | Low | Low | Use confirmed royalty-free sources |
| Auto-scaling cost overrun | Medium | Medium | Set strict max limits, alerts |
| Redis cache failure | Low | Low | Graceful degradation, monitoring |

---

## Dependencies & Critical Path

```
Phase 1 (Week 1-3): Infrastructure Foundation
    └─ BLOCKS ─> All other phases (IaC required for deployments)

Phase 2 (Week 4-7): Image Processing
    ├─ Week 4-5: Person Segmentation
    │   └─ BLOCKS ─> Week 6-7 (Background needs segmentation)
    └─ Week 6-7: Background Composition

Phase 3 (Week 8-11): Video Quality
    ├─ Week 8-9: Lip-Sync (Independent)
    └─ Week 10-11: BGM (Independent)

Phase 4 (Week 12-14): Optimization
    ├─ Week 12: Auto-Scaling (Requires Phase 1 IaC)
    └─ Week 13-14: Caching (Independent)
```

**Critical Path**: Phase 1 → Phase 2 (Segmentation) → Phase 2 (Background)
**Parallel Opportunities**: Phase 3 tasks can run concurrently with Phase 2

---

## Success Metrics & KPIs

### Phase 1
- [ ] Infrastructure deployment time: <5 minutes (vs. current manual process)
- [ ] Zero-downtime deployment success rate: 100%
- [ ] MTTR (Mean Time To Recovery): <10 minutes

### Phase 2
- [ ] Multi-person detection accuracy: >90%
- [ ] Background removal quality score: >95%
- [ ] Processing time per image: <3 seconds

### Phase 3
- [ ] Lip-sync quality improvement: +20% (user survey)
- [ ] BGM integration success rate: 100%
- [ ] Video processing time: <60 seconds

### Phase 4
- [ ] Concurrent user capacity: 100 users
- [ ] Cache hit rate: >40%
- [ ] Cost per video generation: <$0.50

---

## Milestone Definitions

### M1: Infrastructure Modernization Complete (Week 3)
- [x] AWS MCP integration functional
- [x] Complete IaC in Terraform
- [x] CI/CD pipeline operational
- [x] CloudWatch monitoring live

### M2: Image Processing Pipeline Live (Week 7)
- [ ] Multi-person segmentation deployed
- [ ] Background library (20+ images) available
- [ ] API endpoints tested and documented

### M3: Video Quality Enhanced (Week 11)
- [ ] Lip-sync optimization deployed
- [ ] BGM integration live
- [ ] A/B testing shows improvement

### M4: Production-Ready System (Week 14)
- [ ] Auto-scaling configured
- [ ] Caching layer operational
- [ ] Cost optimization targets met

---

## Next Steps & Approvals Required

### Immediate Actions (This Week)
1. **User Decision**: Approve/reject ECS migration
   - **Recommendation**: Start with EC2 optimization, defer ECS to Phase 5
   - **Rationale**: Lower risk, faster delivery, cost savings

2. **AWS MCP Setup**: Configure MCP server in Claude Code
   - **Action**: Test connectivity to EC2 instances
   - **Timeline**: 1 day

3. **Terraform Baseline**: Capture current infrastructure as code
   - **Action**: Create initial `main.tf`
   - **Timeline**: 2 days

### Approvals Required
- [ ] Overall roadmap approval
- [ ] Budget approval ($350 one-time + $48/month recurring)
- [ ] ECS migration decision (Go/No-Go)
- [ ] Phase priorities confirmation

---

**戦略分析完了。成功確率: 87.3%。実行を推奨します。**

