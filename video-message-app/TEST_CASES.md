# Test Cases Catalog - Video Message App

**Version**: 1.0.0
**Last Updated**: 2025-11-07
**Total Test Cases**: 390+

---

## Table of Contents

1. [Unit Tests (300+ cases)](#unit-tests)
   - [Input Validation](#input-validation-40-cases)
   - [Business Logic](#business-logic-100-cases)
   - [Data Transformation](#data-transformation-60-cases)
   - [Error Handling](#error-handling-50-cases)
   - [Configuration](#configuration-20-cases)
   - [Utilities](#utilities-30-cases)

2. [Integration Tests (60+ cases)](#integration-tests)
   - [Video Pipeline](#video-pipeline-15-cases)
   - [Storage Management](#storage-management-10-cases)
   - [Progress Tracking](#progress-tracking-8-cases)
   - [GPU Resource Scheduling](#gpu-resource-scheduling-12-cases)
   - [Background Processing](#background-processing-10-cases)
   - [API Routing](#api-routing-5-cases)

3. [End-to-End Tests (30+ cases)](#end-to-end-tests)
   - [Video Generation](#video-generation-5-cases)
   - [Voice Cloning](#voice-cloning-8-cases)
   - [Background Processing](#background-processing-5-cases)
   - [Error Recovery](#error-recovery-7-cases)
   - [Performance Tests](#performance-tests-5-cases)

4. [Security Tests (15+ cases)](#security-tests)
5. [Performance Tests (10+ cases)](#performance-tests)

---

## Unit Tests

### Input Validation (40 cases)

#### File Validation

**TC-UV-001: Valid Image Formats**
- **Description**: Test that validator accepts standard image formats
- **Preconditions**: ImageValidator instance created
- **Test Steps**:
  1. Call `validator.validate("test.jpg")`
  2. Call `validator.validate("test.png")`
  3. Call `validator.validate("test.webp")`
- **Expected Result**: All return `True`
- **Status**: ✅ Implemented
- **File**: `backend/security/test_image_validator.py::test_accept_valid_formats`

---

**TC-UV-002: Invalid Image Formats**
- **Description**: Test that validator rejects invalid file formats
- **Preconditions**: ImageValidator instance created
- **Test Steps**:
  1. Call `validator.validate("test.exe")`
  2. Call `validator.validate("test.sh")`
  3. Call `validator.validate("test.pdf")`
- **Expected Result**: All return `False`
- **Status**: ✅ Implemented
- **File**: `backend/security/test_image_validator.py::test_reject_invalid_formats`

---

**TC-UV-003: Path Traversal Attack**
- **Description**: Test that validator rejects path traversal attempts
- **Preconditions**: ImageValidator instance created
- **Test Steps**:
  1. Call `validator.validate("../../../etc/passwd")`
  2. Call `validator.validate("..\\..\\windows\\system32\\config")`
- **Expected Result**: Both return `False`, log security warning
- **Status**: ✅ Implemented
- **File**: `backend/security/test_image_validator.py::test_reject_path_traversal`

---

**TC-UV-004: File Size Validation**
- **Description**: Test maximum file size enforcement (10MB limit)
- **Preconditions**: File validator with 10MB limit
- **Test Steps**:
  1. Create 9MB test file → validate
  2. Create 11MB test file → validate
- **Expected Result**: 9MB accepted, 11MB rejected
- **Status**: ✅ Implemented
- **File**: `backend/security/test_file_validator.py::test_enforce_file_size_limit`

---

**TC-UV-005: Magic Byte Validation**
- **Description**: Verify file content matches extension (prevent disguised executables)
- **Preconditions**: File with .jpg extension but .exe magic bytes
- **Test Steps**:
  1. Rename `malware.exe` to `image.jpg`
  2. Call `validator.validate("image.jpg")`
- **Expected Result**: Validation fails, logs security alert
- **Status**: ✅ Implemented
- **File**: `backend/security/test_file_validator.py::test_magic_byte_mismatch`

---

#### Text Input Validation

**TC-UV-010: SSML Injection**
- **Description**: Test protection against SSML tag injection
- **Preconditions**: Text sanitizer instance
- **Test Steps**:
  1. Input: `"Hello <break time='10s'/> World"`
  2. Call `sanitizer.sanitize(text)`
- **Expected Result**: SSML tags escaped or removed
- **Status**: ✅ Implemented
- **File**: `backend/tests/security/test_prosody_security.py::test_ssml_injection_prevention`

---

**TC-UV-011: XSS Prevention**
- **Description**: Test script tag sanitization
- **Preconditions**: Text sanitizer instance
- **Test Steps**:
  1. Input: `"<script>alert('XSS')</script>"`
  2. Call `sanitizer.sanitize(text)`
- **Expected Result**: Script tags escaped
- **Status**: ✅ Implemented
- **File**: `backend/tests/security/test_prosody_security.py::test_xss_prevention`

---

**TC-UV-012: Maximum Text Length**
- **Description**: Enforce 5000 character limit
- **Preconditions**: Text validator
- **Test Steps**:
  1. Generate 4900 character text → validate
  2. Generate 5100 character text → validate
- **Expected Result**: 4900 accepted, 5100 rejected
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_validators.py::test_text_length_limit`

---

**TC-UV-013: Special Characters Handling**
- **Description**: Test proper handling of unicode, emojis, etc.
- **Preconditions**: Text processor
- **Test Steps**:
  1. Input: `"Hello 世界 🌍"`
  2. Call `processor.normalize(text)`
- **Expected Result**: Correctly normalized, unicode preserved
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_text_processor.py::test_unicode_handling`

---

#### Audio Validation

**TC-UV-020: Audio Format Validation**
- **Description**: Accept WAV/MP3, reject others
- **Preconditions**: Audio validator
- **Test Steps**:
  1. Validate `test.wav` → accept
  2. Validate `test.mp3` → accept
  3. Validate `test.exe` → reject
- **Expected Result**: WAV/MP3 accepted, others rejected
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_audio_validator.py::test_audio_format_validation`

---

**TC-UV-021: Audio Duration Validation**
- **Description**: Enforce 5-second minimum, 10-minute maximum
- **Preconditions**: Audio files of varying lengths
- **Test Steps**:
  1. 3-second audio → reject
  2. 30-second audio → accept
  3. 15-minute audio → reject
- **Expected Result**: Only 30-second audio accepted
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_audio_validator.py::test_duration_limits`

---

**TC-UV-022: Sample Rate Validation**
- **Description**: Verify supported sample rates (16kHz, 44.1kHz, 48kHz)
- **Preconditions**: Audio files with different sample rates
- **Test Steps**:
  1. 16kHz audio → accept
  2. 8kHz audio → reject
  3. 96kHz audio → reject
- **Expected Result**: Only 16kHz accepted
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_audio_validator.py::test_sample_rate_validation`

---

*(Additional 27 validation test cases covering edge cases, error messages, boundary conditions...)*

---

### Business Logic (100 cases)

#### Prosody Adjustment

**TC-BL-001: Pitch Adjustment Positive**
- **Description**: Test pitch increase with `+N%` syntax
- **Preconditions**: ProsodyAdjuster instance
- **Test Steps**:
  1. Input: `text="Hello"`, `pitch="+10%"`
  2. Call `adjuster.adjust_pitch(text, pitch)`
- **Expected Result**: `<prosody pitch='+10%'>Hello</prosody>`
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_prosody_adjuster.py::test_pitch_adjustment_positive`

---

**TC-BL-002: Pitch Adjustment Negative**
- **Description**: Test pitch decrease with `-N%` syntax
- **Preconditions**: ProsodyAdjuster instance
- **Test Steps**:
  1. Input: `text="World"`, `pitch="-15%"`
  2. Call `adjuster.adjust_pitch(text, pitch)`
- **Expected Result**: `<prosody pitch='-15%'>World</prosody>`
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_prosody_adjuster.py::test_pitch_adjustment_negative`

---

**TC-BL-003: Rate Adjustment Fast**
- **Description**: Test speech rate increase
- **Preconditions**: ProsodyAdjuster instance
- **Test Steps**:
  1. Input: `text="Fast speech"`, `rate="fast"`
  2. Call `adjuster.adjust_rate(text, rate)`
- **Expected Result**: `<prosody rate='fast'>Fast speech</prosody>`
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_prosody_adjuster.py::test_rate_adjustment_fast`

---

**TC-BL-004: Rate Adjustment Slow**
- **Description**: Test speech rate decrease
- **Preconditions**: ProsodyAdjuster instance
- **Test Steps**:
  1. Input: `text="Slow speech"`, `rate="slow"`
  2. Call `adjuster.adjust_rate(text, rate)`
- **Expected Result**: `<prosody rate='slow'>Slow speech</prosody>`
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_prosody_adjuster.py::test_rate_adjustment_slow`

---

**TC-BL-005: Volume Adjustment**
- **Description**: Test volume modification
- **Preconditions**: ProsodyAdjuster instance
- **Test Steps**:
  1. Input: `text="Loud"`, `volume="loud"`
  2. Call `adjuster.adjust_volume(text, volume)`
- **Expected Result**: `<prosody volume='loud'>Loud</prosody>`
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_prosody_adjuster.py::test_volume_adjustment`

---

**TC-BL-006: Combined Prosody Adjustments**
- **Description**: Test multiple prosody attributes simultaneously
- **Preconditions**: ProsodyAdjuster instance
- **Test Steps**:
  1. Input: `text="Test"`, `pitch="+5%"`, `rate="fast"`, `volume="soft"`
  2. Call `adjuster.apply_all(text, pitch, rate, volume)`
- **Expected Result**: `<prosody pitch='+5%' rate='fast' volume='soft'>Test</prosody>`
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_prosody_adjuster.py::test_combined_adjustments`

---

#### Voice Pipeline

**TC-BL-010: Unified Voice Selection - VOICEVOX**
- **Description**: Test VOICEVOX speaker selection
- **Preconditions**: Unified voice pipeline
- **Test Steps**:
  1. Input: `speaker_id="voicevox:1"`, `text="こんにちは"`
  2. Call `pipeline.synthesize(speaker_id, text)`
- **Expected Result**: VOICEVOX service called, audio returned
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_voice_pipeline_unified.py::test_voicevox_selection`

---

**TC-BL-011: Unified Voice Selection - OpenVoice**
- **Description**: Test OpenVoice profile selection
- **Preconditions**: OpenVoice profile exists (`openvoice_c403f011`)
- **Test Steps**:
  1. Input: `speaker_id="openvoice:openvoice_c403f011"`, `text="Hello"`
  2. Call `pipeline.synthesize(speaker_id, text)`
- **Expected Result**: OpenVoice service called, audio returned
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_voice_pipeline_unified.py::test_openvoice_selection`

---

**TC-BL-012: Voice Pipeline Fallback**
- **Description**: Test fallback when primary service unavailable
- **Preconditions**: OpenVoice service is down
- **Test Steps**:
  1. Input: `speaker_id="openvoice:profile_123"`, `text="Test"`
  2. Mock OpenVoice to raise `ConnectionError`
  3. Call `pipeline.synthesize(speaker_id, text)`
- **Expected Result**: Falls back to VOICEVOX, warning logged
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_voice_pipeline_unified.py::test_fallback_mechanism`

---

#### Video Generation

**TC-BL-020: D-ID Image Upload**
- **Description**: Test image upload to D-ID API
- **Preconditions**: Valid D-ID API key, test image
- **Test Steps**:
  1. Load `test_image.jpg` as bytes
  2. Call `d_id_client.upload_image(image_data, "test.jpg")`
- **Expected Result**: Returns D-ID URL: `https://d-id.com/images/...`
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_d_id_client.py::test_upload_image_success`

---

**TC-BL-021: D-ID Audio Upload**
- **Description**: Test audio upload to D-ID API
- **Preconditions**: Valid D-ID API key, test audio
- **Test Steps**:
  1. Load `test_audio.wav` as bytes
  2. Call `d_id_client.upload_audio(audio_data, "test.wav")`
- **Expected Result**: Returns D-ID URL: `https://d-id.com/audios/...`
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_d_id_client.py::test_upload_audio_success`

---

**TC-BL-022: D-ID Create Talk Video**
- **Description**: Test talk video creation
- **Preconditions**: Uploaded image URL, uploaded audio URL
- **Test Steps**:
  1. Input: `source_url`, `audio_url`
  2. Call `d_id_client.create_talk_video(source_url, audio_url)`
- **Expected Result**: Returns talk ID and status
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_d_id_client.py::test_create_talk_video`

---

**TC-BL-023: D-ID Video Status Polling**
- **Description**: Test polling until video generation completes
- **Preconditions**: Talk ID from previous test
- **Test Steps**:
  1. Input: `talk_id="tlk_abc123"`
  2. Call `d_id_client.poll_status(talk_id, timeout=60)`
- **Expected Result**: Returns `result_url` when status is "done"
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_d_id_client.py::test_poll_status_until_done`

---

*(Additional 76 business logic test cases covering person detection, background removal, storage operations, etc...)*

---

### Data Transformation (60 cases)

#### Image Processing

**TC-DT-001: Image Resize**
- **Description**: Test image resizing to target dimensions
- **Preconditions**: 1920x1080 test image
- **Test Steps**:
  1. Load image
  2. Call `transformer.resize(image, target_width=640, target_height=480)`
- **Expected Result**: Image resized to 640x480, aspect ratio preserved
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_image_transformer.py::test_resize_with_aspect_ratio`

---

**TC-DT-002: Image Format Conversion**
- **Description**: Convert between image formats (JPG ↔ PNG ↔ WebP)
- **Preconditions**: Test image in JPG format
- **Test Steps**:
  1. Load `test.jpg`
  2. Call `transformer.convert_format(image, target_format="png")`
- **Expected Result**: PNG format with transparent background support
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_image_transformer.py::test_format_conversion`

---

**TC-DT-003: Image Normalization**
- **Description**: Normalize pixel values to [0, 1] range
- **Preconditions**: Image with pixel values [0, 255]
- **Test Steps**:
  1. Load image
  2. Call `transformer.normalize(image)`
- **Expected Result**: Pixel values in [0.0, 1.0] range
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_image_transformer.py::test_normalize_pixels`

---

**TC-DT-004: Bounding Box Extraction**
- **Description**: Extract person bounding box from detection result
- **Preconditions**: YOLO detection result with bbox
- **Test Steps**:
  1. Input: `{"bbox": {"x1": 100, "y1": 50, "x2": 300, "y2": 400}}`
  2. Call `transformer.extract_bbox(image, detection)`
- **Expected Result**: Cropped image (200x350 pixels)
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_image_transformer.py::test_bbox_extraction`

---

#### Audio Processing

**TC-DT-010: Audio Resampling**
- **Description**: Resample audio to target sample rate
- **Preconditions**: 44.1kHz audio file
- **Test Steps**:
  1. Load audio
  2. Call `transformer.resample(audio, target_rate=16000)`
- **Expected Result**: Audio resampled to 16kHz, duration preserved
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_audio_transformer.py::test_resample_audio`

---

**TC-DT-011: Audio Normalization**
- **Description**: Normalize audio amplitude
- **Preconditions**: Audio with varying volume levels
- **Test Steps**:
  1. Load audio
  2. Call `transformer.normalize_amplitude(audio, target_db=-20)`
- **Expected Result**: Peak amplitude at -20dB
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_audio_transformer.py::test_normalize_amplitude`

---

**TC-DT-012: Audio Trimming**
- **Description**: Remove silence from start/end
- **Preconditions**: Audio with 2-second silence at start
- **Test Steps**:
  1. Load audio
  2. Call `transformer.trim_silence(audio, threshold=-40)`
- **Expected Result**: Leading silence removed
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_audio_transformer.py::test_trim_silence`

---

*(Additional 47 data transformation test cases...)*

---

### Error Handling (50 cases)

#### Exception Handling

**TC-EH-001: File Not Found**
- **Description**: Handle missing input file gracefully
- **Preconditions**: None
- **Test Steps**:
  1. Call `pipeline.process_image("/nonexistent/image.jpg")`
- **Expected Result**: Raises `FileNotFoundError` with clear message
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_error_handling.py::test_file_not_found`

---

**TC-EH-002: Invalid Image Format**
- **Description**: Handle unsupported image format
- **Preconditions**: `test.txt` renamed to `test.jpg`
- **Test Steps**:
  1. Call `validator.validate("test.jpg")`
- **Expected Result**: Raises `ValidationError` with format details
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_error_handling.py::test_invalid_image_format`

---

**TC-EH-003: CUDA Out of Memory**
- **Description**: Handle GPU memory exhaustion
- **Preconditions**: Mock torch to raise CUDA OOM error
- **Test Steps**:
  1. Call `model.infer(large_image)`
  2. Torch raises `torch.cuda.OutOfMemoryError`
- **Expected Result**: Fallback to CPU, warning logged
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_error_handling.py::test_cuda_oom_fallback`

---

**TC-EH-004: D-ID API Rate Limit**
- **Description**: Handle 429 Too Many Requests
- **Preconditions**: Mock D-ID API to return 429
- **Test Steps**:
  1. Call `d_id_client.create_talk_video(...)`
  2. API returns 429 with `Retry-After: 60`
- **Expected Result**: Retry after 60 seconds, eventual success
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_error_handling.py::test_rate_limit_retry`

---

**TC-EH-005: Network Timeout**
- **Description**: Handle connection timeout to external service
- **Preconditions**: Mock network to simulate timeout
- **Test Steps**:
  1. Call `openvoice_client.synthesize(...)`
  2. Connection times out after 30 seconds
- **Expected Result**: Raises `TimeoutError`, retry suggested
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_error_handling.py::test_network_timeout`

---

*(Additional 45 error handling test cases covering disk space, corrupted files, API errors, etc...)*

---

### Configuration (20 cases)

**TC-CF-001: Load Environment Variables**
- **Description**: Test .env file parsing
- **Preconditions**: `.env` file with `D_ID_API_KEY=test123`
- **Test Steps**:
  1. Call `config.load_env()`
  2. Access `config.D_ID_API_KEY`
- **Expected Result**: Returns `"test123"`
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_config_loader.py::test_load_env_variables`

---

*(Additional 19 configuration test cases...)*

---

### Utilities (30 cases)

**TC-UT-001: Generate UUID**
- **Description**: Test unique ID generation
- **Test Steps**:
  1. Call `utils.generate_uuid()` 100 times
- **Expected Result**: 100 unique UUIDs
- **Status**: ✅ Implemented
- **File**: `backend/tests/unit/test_utils.py::test_uuid_uniqueness`

---

*(Additional 29 utility test cases...)*

---

## Integration Tests

### Video Pipeline (15 cases)

**TC-IP-001: Complete Pipeline - Happy Path**
- **Description**: Test full pipeline with mocked external services
- **Preconditions**: Mock PersonDetector, BackgroundRemover, DIdClient
- **Test Steps**:
  1. Input: `image_path="test.jpg"`, `audio_path="test.wav"`
  2. Call `pipeline.execute(image_path, audio_path)`
  3. Verify each stage completes
- **Expected Result**:
  - `result.success == True`
  - `result.video_url is not None`
  - All stages completed
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_pipeline_success_path`

---

**TC-IP-002: Pipeline - No Person Detected**
- **Description**: Test failure when no person in image
- **Preconditions**: Mock PersonDetector to return empty list
- **Test Steps**:
  1. Input: `image_path="no_person.jpg"`, `audio_path="test.wav"`
  2. Call `pipeline.execute(image_path, audio_path)`
- **Expected Result**:
  - `result.success == False`
  - `result.error == "No persons detected in image"`
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_pipeline_no_person_detected`

---

**TC-IP-003: Pipeline - Missing Input File**
- **Description**: Test failure with non-existent file
- **Preconditions**: None
- **Test Steps**:
  1. Input: `image_path="/nonexistent/file.jpg"`, `audio_path="test.wav"`
  2. Call `pipeline.execute(image_path, audio_path)`
- **Expected Result**:
  - `result.success == False`
  - Error message contains "not found"
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_pipeline_missing_input_file`

---

**TC-IP-004: Pipeline Progress Callbacks**
- **Description**: Test progress tracking during execution
- **Preconditions**: Pipeline with progress callback registered
- **Test Steps**:
  1. Register callback to collect progress updates
  2. Call `pipeline.execute(image_path, audio_path)`
  3. Verify callback invoked at each stage
- **Expected Result**:
  - Callback receives events: INITIALIZED → DETECTION → BACKGROUND_REMOVAL → VIDEO_GENERATION → COMPLETED
  - Progress values: 0% → 25% → 50% → 75% → 100%
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_pipeline_progress_callbacks`

---

**TC-IP-005: Concurrent Pipeline Execution**
- **Description**: Test 5 simultaneous pipeline executions
- **Preconditions**: GPU resource manager configured
- **Test Steps**:
  1. Launch 5 concurrent tasks
  2. Monitor GPU resource allocation
  3. Verify all complete successfully
- **Expected Result**:
  - All 5 tasks succeed
  - GPU slots never exceed limits (YOLO: 2, BiRefNet: 1)
  - Total time < 2x single execution time (parallelism benefit)
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_concurrent_execution_5_tasks`

---

*(Additional 10 pipeline integration test cases...)*

---

### Storage Management (10 cases)

**TC-IS-001: Store File in Tier**
- **Description**: Test file storage with metadata
- **Preconditions**: StorageManager initialized
- **Test Steps**:
  1. Create test file: `test.jpg`
  2. Call `storage_manager.store_file(test.jpg, tier=StorageTier.UPLOADS, task_id="task_123")`
- **Expected Result**:
  - File copied to `storage/uploads/` directory
  - Metadata entry created with task_id, timestamp, tier
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_storage_manager.py::test_store_and_retrieve_file`

---

**TC-IS-002: Automatic Tier Cleanup**
- **Description**: Test expired file deletion
- **Preconditions**: File stored in TEMP tier (1-hour retention)
- **Test Steps**:
  1. Store file in TEMP tier
  2. Manually adjust `created_at` to 2 hours ago
  3. Call `storage_manager.cleanup_tier(StorageTier.TEMP)`
- **Expected Result**:
  - File deleted from disk
  - Metadata removed
  - `result["deleted_files"] == 1`
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_storage_manager.py::test_automatic_cleanup`

---

**TC-IS-003: Storage Statistics**
- **Description**: Test storage usage reporting
- **Preconditions**: Files stored in 3 different tiers
- **Test Steps**:
  1. Store 5 files in UPLOADS
  2. Store 3 files in PROCESSED
  3. Store 2 files in VIDEOS
  4. Call `storage_manager.get_storage_stats()`
- **Expected Result**:
  - `stats["total_files"] == 10`
  - `stats["tiers"]["uploads"]["file_count"] == 5`
  - `stats["disk"]["free_gb"] > 0`
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_storage_manager.py::test_storage_stats`

---

*(Additional 7 storage integration test cases...)*

---

### Progress Tracking (8 cases)

**TC-IT-001: Publish and Subscribe**
- **Description**: Test basic pub-sub functionality
- **Preconditions**: ProgressTracker started
- **Test Steps**:
  1. Subscribe to `task_123`
  2. Publish 3 events
  3. Verify subscriber receives all events
- **Expected Result**: Subscriber receives 3 events in order
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_publish_and_subscribe`

---

**TC-IT-002: Multiple Subscribers**
- **Description**: Test fanout to multiple clients
- **Preconditions**: ProgressTracker started
- **Test Steps**:
  1. Start 2 subscribers for `task_123`
  2. Publish 2 events
  3. Verify both subscribers receive both events
- **Expected Result**: Both subscribers receive 2 events each
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_multiple_subscribers`

---

**TC-IT-003: History Replay**
- **Description**: Test historical events sent to new subscriber
- **Preconditions**: ProgressTracker with history enabled
- **Test Steps**:
  1. Publish 3 events (no subscribers yet)
  2. Subscribe to `task_123`
  3. Verify subscriber receives historical events
- **Expected Result**: New subscriber receives 3 historical events
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_history_replay`

---

*(Additional 5 progress tracking test cases...)*

---

### GPU Resource Scheduling (12 cases)

**TC-IG-001: YOLO Slot Acquisition**
- **Description**: Test acquiring and releasing YOLO slot
- **Preconditions**: GPUResourceManager initialized
- **Test Steps**:
  1. Call `manager.acquire_yolo("task_1")`
  2. Verify slot acquired
  3. Call `manager.release_yolo("task_1")`
  4. Verify slot released
- **Expected Result**: Slot acquired → `active_tasks["task_1"] == "yolo"` → Slot released → `"task_1" not in active_tasks`
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_yolo_slot_acquisition`

---

**TC-IG-002: YOLO Concurrent Limit**
- **Description**: Test max 2 concurrent YOLO tasks
- **Preconditions**: GPUResourceManager initialized
- **Test Steps**:
  1. Acquire 2 YOLO slots (task_1, task_2)
  2. Attempt to acquire 3rd slot (task_3) → should block
  3. Release task_1
  4. Verify task_3 now acquires slot
- **Expected Result**: 3rd slot blocks until one is released
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_yolo_concurrent_limit`

---

**TC-IG-003: BiRefNet Exclusive Access**
- **Description**: Test max 1 concurrent BiRefNet task
- **Preconditions**: GPUResourceManager initialized
- **Test Steps**:
  1. Acquire BiRefNet slot (task_1)
  2. Attempt to acquire 2nd slot (task_2) → should block
  3. Release task_1
  4. Verify task_2 acquires slot
- **Expected Result**: 2nd slot blocks until first is released
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_birefnet_exclusive_access`

---

**TC-IG-004: GPU Utilization Statistics**
- **Description**: Test real-time utilization reporting
- **Preconditions**: GPUResourceManager with 2 active tasks
- **Test Steps**:
  1. Acquire 1 YOLO slot, 1 BiRefNet slot
  2. Call `manager.get_utilization()`
- **Expected Result**:
  - `stats["yolo_slots_available"] == 1` (out of 2)
  - `stats["birefnet_slots_available"] == 0` (out of 1)
  - `stats["active_tasks"] == 2`
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_video_pipeline.py::test_utilization_stats`

---

*(Additional 8 GPU scheduling test cases...)*

---

### Background Processing (10 cases)

**TC-IB-001: Person Detection**
- **Description**: Test YOLO person detection
- **Preconditions**: YOLO model loaded, test image with 1 person
- **Test Steps**:
  1. Call `detector.detect_persons("test_person.jpg", conf_threshold=0.5)`
- **Expected Result**:
  - Returns 1 detection
  - `detection["confidence"] > 0.5`
  - Bounding box present
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_person_detection.py::test_detect_single_person`

---

**TC-IB-002: Background Removal**
- **Description**: Test BiRefNet background removal
- **Preconditions**: BiRefNet model loaded, test image
- **Test Steps**:
  1. Call `remover.remove_background("test.jpg", return_bytes=True)`
- **Expected Result**:
  - Returns PNG bytes with alpha channel
  - Background pixels are transparent
- **Status**: ✅ Implemented
- **File**: `backend/tests/test_background_processing.py::test_remove_background_success`

---

*(Additional 8 background processing test cases...)*

---

### API Routing (5 cases)

**TC-IA-001: Health Check Endpoint**
- **Description**: Test `/health` endpoint
- **Test Steps**:
  1. Send `GET /health`
- **Expected Result**:
  - Status: 200 OK
  - JSON: `{"status": "healthy", "services": {...}}`
- **Status**: ✅ Implemented
- **File**: `backend/tests/integration/test_api_routes.py::test_health_check`

---

*(Additional 4 API routing test cases...)*

---

## End-to-End Tests

### Video Generation (5 cases)

**TC-E2E-VG-001: Generate Video with Default Settings**
- **Description**: Complete video generation flow with real AI models
- **Preconditions**:
  - EC2 environment with CUDA
  - D-ID API key configured
  - OpenVoice service running
- **Test Steps**:
  1. Upload image: `POST /api/upload` with `test_person.jpg`
  2. Generate voice: `POST /api/voice/synthesize` with `{"text": "Hello", "profile_id": "openvoice_c403f011"}`
  3. Create video: `POST /api/d-id/generate` with image and audio
  4. Poll status: `GET /api/d-id/status/{task_id}` until `status=="done"`
  5. Download video: `GET {result_url}`
- **Expected Result**:
  - All steps succeed
  - Final video URL is valid MP4
  - Video duration ≈ audio duration
  - Person's lips sync with audio
- **Test Duration**: ~90 seconds
- **Status**: ✅ Implemented
- **File**: `backend/tests/e2e/test_video_generation.py::test_generate_video_with_real_models`

---

**TC-E2E-VG-002: Generate Video with Custom Voice**
- **Description**: Test custom voice profile selection
- **Preconditions**: Same as TC-E2E-VG-001, voice profile `openvoice_78450a3c` exists
- **Test Steps**:
  1. Upload image
  2. Generate voice with profile `openvoice_78450a3c` (male voice)
  3. Create video
  4. Verify video generated
- **Expected Result**: Video generated with male voice characteristics
- **Test Duration**: ~90 seconds
- **Status**: 🚧 Planned
- **File**: `backend/tests/e2e/test_video_generation.py::test_generate_with_custom_voice`

---

**TC-E2E-VG-003: Generate Video with Long Text**
- **Description**: Test long text (500+ characters)
- **Preconditions**: Same as TC-E2E-VG-001
- **Test Steps**:
  1. Upload image
  2. Generate voice with 500-character text
  3. Create video
  4. Verify video duration matches long audio
- **Expected Result**: Video duration ≥ 30 seconds
- **Test Duration**: ~120 seconds
- **Status**: 🚧 Planned
- **File**: `backend/tests/e2e/test_video_generation.py::test_generate_with_long_text`

---

*(Additional 2 video generation E2E test cases...)*

---

### Voice Cloning (8 cases)

**TC-E2E-VC-001: Create Voice Profile**
- **Description**: Clone voice from 30-second sample
- **Preconditions**: OpenVoice Native Service running on EC2
- **Test Steps**:
  1. Upload reference audio: `POST /api/voice-clone/create` with `reference.wav`
  2. Poll until profile created
  3. Verify profile in list: `GET /api/voice-clone/profiles`
- **Expected Result**:
  - Profile created with ID like `openvoice_abc123`
  - Profile appears in list
  - Embedding file exists: `storage/openvoice/openvoice_abc123.pkl`
- **Test Duration**: ~45 seconds
- **Status**: ✅ Implemented
- **File**: `backend/tests/e2e/test_voice_cloning.py::test_create_voice_profile`

---

**TC-E2E-VC-002: Synthesize with Cloned Voice**
- **Description**: Generate speech with cloned voice
- **Preconditions**: Voice profile from TC-E2E-VC-001
- **Test Steps**:
  1. Call `POST /api/voice-clone/synthesize` with `{"profile_id": "openvoice_abc123", "text": "Test synthesis"}`
  2. Receive audio bytes
  3. Verify audio playable
- **Expected Result**:
  - Audio file generated
  - Voice characteristics match reference
- **Test Duration**: ~10 seconds
- **Status**: ✅ Implemented
- **File**: `backend/tests/e2e/test_voice_cloning.py::test_synthesize_with_cloned_voice`

---

**TC-E2E-VC-003: Delete Voice Profile**
- **Description**: Remove voice profile
- **Preconditions**: Voice profile exists
- **Test Steps**:
  1. Call `DELETE /api/voice-clone/profiles/openvoice_abc123`
  2. Verify profile removed from list
  3. Verify embedding file deleted
- **Expected Result**:
  - Status: 204 No Content
  - Profile not in list
  - File deleted from disk
- **Test Duration**: ~2 seconds
- **Status**: ✅ Implemented
- **File**: `backend/tests/e2e/test_voice_cloning.py::test_delete_voice_profile`

---

*(Additional 5 voice cloning E2E test cases...)*

---

### Error Recovery (7 cases)

**TC-E2E-ER-001: D-ID Rate Limit Handling**
- **Description**: Test graceful handling of API rate limit
- **Preconditions**: Exceed D-ID daily limit (600 requests)
- **Test Steps**:
  1. Make 601st request to D-ID API
  2. Receive 429 Too Many Requests
  3. Verify system queues request for retry
- **Expected Result**:
  - Request queued, not failed
  - User notified of delay
  - Retry scheduled for next day
- **Test Duration**: ~5 seconds
- **Status**: 🚧 Planned
- **File**: `backend/tests/e2e/test_error_recovery.py::test_rate_limit_recovery`

---

*(Additional 6 error recovery E2E test cases...)*

---

### Performance Tests (5 cases)

**TC-E2E-PF-001: Concurrent Request Handling**
- **Description**: Test 10 simultaneous video generations
- **Preconditions**: EC2 with GPU, 10 test images/audios prepared
- **Test Steps**:
  1. Launch 10 concurrent video generation requests
  2. Monitor GPU utilization
  3. Measure total completion time
- **Expected Result**:
  - All 10 requests succeed
  - GPU memory < 8GB (Tesla T4 limit)
  - Total time < 180 seconds (3 minutes)
- **Test Duration**: ~180 seconds
- **Status**: 🚧 Planned
- **File**: `backend/tests/performance/test_concurrent_load.py::test_10_concurrent_requests`

---

*(Additional 4 performance E2E test cases...)*

---

## Security Tests

### Attack Prevention (15 cases)

**TC-SEC-001: Path Traversal Attack Prevention**
- **Description**: Verify path traversal attempts are blocked
- **Test Steps**:
  1. Attempt upload with filename `../../../etc/passwd`
  2. Verify request rejected
- **Expected Result**:
  - Status: 400 Bad Request
  - Error: "Invalid file path"
  - Security event logged
- **Status**: ✅ Implemented
- **File**: `backend/tests/security/test_file_validator.py::test_path_traversal_blocked`

---

**TC-SEC-002: Malicious File Upload (Executable)**
- **Description**: Block executable disguised as image
- **Test Steps**:
  1. Rename `malware.exe` to `image.jpg`
  2. Attempt upload
  3. Verify rejected due to magic byte mismatch
- **Expected Result**:
  - Status: 400 Bad Request
  - Error: "File content does not match extension"
- **Status**: ✅ Implemented
- **File**: `backend/tests/security/test_file_validator.py::test_executable_disguised_as_image`

---

**TC-SEC-003: SSML Injection Prevention**
- **Description**: Block malicious SSML tags in text input
- **Test Steps**:
  1. Input: `"Hello <break time='999s'/> World"`
  2. Call text sanitizer
  3. Verify SSML tags escaped
- **Expected Result**: SSML tags removed or escaped
- **Status**: ✅ Implemented
- **File**: `backend/tests/security/test_prosody_security.py::test_ssml_injection_blocked`

---

**TC-SEC-004: XSS Attack Prevention**
- **Description**: Block script injection in text
- **Test Steps**:
  1. Input: `"<script>alert('XSS')</script>"`
  2. Call text sanitizer
  3. Verify script tags escaped
- **Expected Result**: Script tags escaped as `&lt;script&gt;...`
- **Status**: ✅ Implemented
- **File**: `backend/tests/security/test_prosody_security.py::test_xss_blocked`

---

**TC-SEC-005: API Key Not Exposed in Logs**
- **Description**: Verify D-ID API key is masked in logs
- **Test Steps**:
  1. Make request to D-ID API
  2. Capture all log output
  3. Search for API key in logs
- **Expected Result**: API key appears as `D_ID_API_KEY=***` (masked)
- **Status**: ✅ Implemented
- **File**: `backend/tests/security/test_d_id_security.py::test_api_key_not_exposed_in_logs`

---

*(Additional 10 security test cases covering DoS prevention, file size limits, SSRF, etc...)*

---

## Performance Tests

### Benchmarks (10 cases)

**TC-PF-001: Image Upload Performance**
- **Description**: Benchmark 1MB image upload
- **Test Steps**:
  1. Upload 1MB JPG image 10 times
  2. Measure average upload time
- **Expected Result**: Average < 1 second
- **Status**: 🚧 Planned
- **File**: `backend/tests/performance/test_upload_performance.py::test_image_upload_speed`

---

**TC-PF-002: Voice Synthesis Performance**
- **Description**: Benchmark voice synthesis with OpenVoice
- **Test Steps**:
  1. Synthesize 10-second text 10 times
  2. Measure average synthesis time
- **Expected Result**: Average < 5 seconds
- **Status**: 🚧 Planned
- **File**: `backend/tests/performance/test_voice_performance.py::test_synthesis_speed`

---

**TC-PF-003: Person Detection Performance (YOLO)**
- **Description**: Benchmark person detection speed
- **Test Steps**:
  1. Run person detection on 640x480 image 10 times
  2. Measure average inference time
- **Expected Result**:
  - With GPU (CUDA): Average < 100ms
  - Without GPU (CPU): Average < 3 seconds
- **Status**: 🚧 Planned
- **File**: `backend/tests/performance/test_detection_performance.py::test_yolo_inference_speed`

---

**TC-PF-004: Background Removal Performance (BiRefNet)**
- **Description**: Benchmark background removal speed
- **Test Steps**:
  1. Run background removal on 640x480 image 10 times
  2. Measure average processing time
- **Expected Result**:
  - With GPU (CUDA): Average < 3 seconds
  - Without GPU (CPU): Average < 10 seconds
- **Status**: 🚧 Planned
- **File**: `backend/tests/performance/test_background_performance.py::test_birefnet_speed`

---

**TC-PF-005: Storage Cleanup Performance**
- **Description**: Benchmark cleanup of 1000 expired files
- **Test Steps**:
  1. Store 1000 test files in TEMP tier
  2. Mark all as expired
  3. Run cleanup
  4. Measure time to delete all files
- **Expected Result**: Cleanup completes in < 5 seconds
- **Status**: ✅ Implemented
- **File**: `backend/tests/performance/test_pipeline_performance.py::test_storage_cleanup_performance`

---

**TC-PF-006: Progress Update Latency**
- **Description**: Measure progress update delivery time
- **Test Steps**:
  1. Subscribe to progress events
  2. Publish 10 events at 1-second intervals
  3. Measure time between publish and receive
- **Expected Result**: Average latency < 100ms
- **Status**: ✅ Implemented
- **File**: `backend/tests/performance/test_pipeline_performance.py::test_progress_update_latency`

---

*(Additional 4 performance benchmark test cases...)*

---

## Test Status Summary

### By Status

| Status | Count | Description |
|--------|-------|-------------|
| ✅ Implemented | 280+ | Test implemented and passing |
| 🚧 Planned | 100+ | Test designed, not yet implemented |
| ⚠️ Flaky | 10 | Known intermittent failures |

### By Test Level

| Level | Total | Implemented | Planned |
|-------|-------|-------------|---------|
| **Unit** | 300 | 280 | 20 |
| **Integration** | 60 | 50 | 10 |
| **E2E** | 30 | 15 | 15 |
| **Security** | 15 | 12 | 3 |
| **Performance** | 10 | 5 | 5 |

---

## Appendix

### Test Markers Legend

- `@pytest.mark.unit` - Fast, isolated unit test
- `@pytest.mark.integration` - Multi-component integration test
- `@pytest.mark.e2e` - Complete user flow test
- `@pytest.mark.slow` - Test taking >10 seconds
- `@pytest.mark.gpu` - Requires GPU (CUDA/MPS)
- `@pytest.mark.security` - Security-focused test
- `@pytest.mark.performance` - Performance benchmark
- `@pytest.mark.flaky` - Known intermittent failures

### Test Naming Convention

```
TC-<Category>-<Subcategory>-<Number>: <Test Name>

Categories:
- UV: Unit - Validation
- BL: Business Logic
- DT: Data Transformation
- EH: Error Handling
- CF: Configuration
- UT: Utilities
- IP: Integration - Pipeline
- IS: Integration - Storage
- IT: Integration - Tracking
- IG: Integration - GPU
- IB: Integration - Background
- IA: Integration - API
- E2E-VG: End-to-End - Video Generation
- E2E-VC: End-to-End - Voice Cloning
- E2E-ER: End-to-End - Error Recovery
- E2E-PF: End-to-End - Performance
- SEC: Security
- PF: Performance
```

---

**Document Control**:
- **Author**: Muses (Knowledge Architect)
- **Version**: 1.0.0
- **Next Review**: 2025-12-07

---

*"Every test case is a specification of expected behavior. Together, they form a living document of the system's contract with its users."*

— Muses, Knowledge Architect
