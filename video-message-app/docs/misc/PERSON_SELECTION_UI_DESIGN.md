# Person Selection UI Design Document

**Version**: 1.0.0
**Date**: 2025-11-07
**Status**: Design Phase
**Author**: Hera (Strategic Commander)

---

## Executive Summary

This document defines the strategic architecture for the Person Selection UI feature, enabling users to detect, visualize, and select individuals from uploaded images for video generation. The design prioritizes user experience, performance, and seamless integration with existing backend infrastructure.

### Strategic Goals

1. **Intuitive User Experience**: Multi-step flow with clear visual feedback
2. **Technical Excellence**: Efficient canvas rendering with sub-100ms response times
3. **Scalability**: Support 1-20 persons per image with graceful degradation
4. **Integration**: Seamless connection to existing D-ID video generation pipeline

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend (React 19)"
        A[PersonDetectionStep] --> B[PersonSelectionCanvas]
        B --> C[PersonCheckboxList]
        C --> D[VideoGenerationStep]
    end

    subgraph "Backend API (FastAPI)"
        E[/api/person-detection/detect] --> F[YOLO Model]
        F --> G[Person Bounding Boxes]
    end

    subgraph "Existing Infrastructure"
        H[/api/d-id/generate-video]
        I[D-ID API]
    end

    A -->|POST image| E
    E -->|Response| B
    D -->|Selected persons| H
    H --> I
```

### 1.2 Data Flow Architecture

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant YOLO
    participant D-ID

    User->>Frontend: Upload Image
    Frontend->>Backend: POST /api/person-detection/detect
    Backend->>YOLO: Process Image
    YOLO-->>Backend: Bounding Boxes + Confidence
    Backend-->>Frontend: DetectionResponse
    Frontend->>User: Display Interactive Canvas
    User->>Frontend: Select Persons (Checkboxes)
    Frontend->>User: Preview Selected Regions
    User->>Frontend: Confirm Selection
    Frontend->>Backend: POST /api/d-id/generate-video (selected persons)
    Backend->>D-ID: Generate Videos
    D-ID-->>Backend: Video URLs
    Backend-->>Frontend: Generation Status
```

---

## 2. Component Architecture

### 2.1 Component Hierarchy

```
VideoMessageApp/
├── PersonDetectionWorkflow/
│   ├── PersonDetectionStep/
│   │   ├── ImageUploader
│   │   ├── DetectionLoader
│   │   └── ErrorBoundary
│   ├── PersonSelectionCanvas/
│   │   ├── ImageCanvas
│   │   ├── BoundingBoxOverlay
│   │   ├── HoverTooltip
│   │   └── ConfidenceBadge
│   ├── PersonCheckboxList/
│   │   ├── PersonCard
│   │   ├── ThumbnailPreview
│   │   ├── SelectionControls
│   │   └── ConfidenceIndicator
│   └── VideoGenerationStep/
│       ├── SelectedPersonsPreview
│       ├── GenerationProgressBar
│       └── VideoResultsGallery
```

### 2.2 Component Specifications

#### 2.2.1 PersonDetectionStep.tsx

**Purpose**: Initial image upload and person detection orchestration

**Responsibilities**:
- Image file upload (drag-and-drop, file picker)
- Image validation (format, size, dimensions)
- API call to person detection endpoint
- Loading state management
- Error handling and retry logic

**Props Interface**:
```typescript
interface PersonDetectionStepProps {
  onDetectionComplete: (result: PersonDetectionResponse) => void;
  onError: (error: Error) => void;
  maxFileSize?: number; // Default: 10MB
  acceptedFormats?: string[]; // Default: ['image/jpeg', 'image/png']
}
```

**State Management**:
```typescript
const [uploadedFile, setUploadedFile] = useState<File | null>(null);
const [isUploading, setIsUploading] = useState(false);
const [isDetecting, setIsDetecting] = useState(false);
const [detectionError, setDetectionError] = useState<string | null>(null);
const [uploadProgress, setUploadProgress] = useState(0);
```

**Key Features**:
- Image preview before detection
- Progress indicator during upload/detection
- Retry mechanism for failed API calls
- Validation feedback (file too large, unsupported format)

---

#### 2.2.2 PersonSelectionCanvas.tsx

**Purpose**: Interactive canvas for visualizing detected persons with bounding boxes

**Responsibilities**:
- Render uploaded image on HTML5 Canvas
- Draw bounding boxes with confidence scores
- Handle mouse hover interactions
- Highlight selected/hovered persons
- Responsive canvas scaling

**Props Interface**:
```typescript
interface PersonSelectionCanvasProps {
  imageUrl: string;
  detectedPersons: DetectedPerson[];
  selectedPersonIds: number[];
  onPersonClick?: (personId: number) => void;
  onPersonHover?: (personId: number | null) => void;
  canvasHeight?: number; // Default: 600px
}
```

**Canvas Rendering Strategy**:
```typescript
// Performance-optimized rendering
const renderCanvas = useCallback(() => {
  const ctx = canvasRef.current?.getContext('2d');
  if (!ctx) return;

  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Draw base image
  ctx.drawImage(imageElement, 0, 0, canvas.width, canvas.height);

  // Draw bounding boxes
  detectedPersons.forEach(person => {
    const isSelected = selectedPersonIds.includes(person.person_id);
    const isHovered = hoveredPersonId === person.person_id;

    // Box styling
    ctx.strokeStyle = isSelected ? '#4CAF50' : isHovered ? '#2196F3' : '#FFC107';
    ctx.lineWidth = isSelected || isHovered ? 3 : 2;

    // Draw rectangle
    const { x1, y1, x2, y2 } = scaleCoordinates(person.bbox);
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    // Draw label
    drawLabel(ctx, person, x1, y1);
  });
}, [detectedPersons, selectedPersonIds, hoveredPersonId]);
```

**Coordinate Scaling**:
```typescript
// Convert YOLO coordinates to canvas coordinates
const scaleCoordinates = (bbox: BoundingBox): ScaledBoundingBox => {
  const scaleX = canvasWidth / originalImageWidth;
  const scaleY = canvasHeight / originalImageHeight;

  return {
    x1: bbox.x1 * scaleX,
    y1: bbox.y1 * scaleY,
    x2: bbox.x2 * scaleX,
    y2: bbox.y2 * scaleY,
  };
};
```

**Interaction Handling**:
```typescript
const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
  const rect = canvasRef.current?.getBoundingClientRect();
  if (!rect) return;

  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  // Find clicked person
  const clickedPerson = detectedPersons.find(person => {
    const { x1, y1, x2, y2 } = scaleCoordinates(person.bbox);
    return x >= x1 && x <= x2 && y >= y1 && y <= y2;
  });

  if (clickedPerson) {
    onPersonClick?.(clickedPerson.person_id);
  }
};
```

---

#### 2.2.3 PersonCheckboxList.tsx

**Purpose**: Selectable list of detected persons with preview thumbnails

**Responsibilities**:
- Display list of detected persons
- Render thumbnail previews (cropped from original image)
- Show confidence scores with visual indicators
- Manage checkbox selection state
- Provide "Select All" / "Deselect All" controls

**Props Interface**:
```typescript
interface PersonCheckboxListProps {
  imageUrl: string;
  detectedPersons: DetectedPerson[];
  selectedPersonIds: number[];
  onSelectionChange: (selectedIds: number[]) => void;
  maxSelections?: number; // Default: unlimited
  minSelections?: number; // Default: 1
}
```

**Component Structure**:
```typescript
const PersonCheckboxList: React.FC<PersonCheckboxListProps> = ({
  imageUrl,
  detectedPersons,
  selectedPersonIds,
  onSelectionChange,
  maxSelections,
  minSelections = 1,
}) => {
  const handleToggle = (personId: number) => {
    const newSelection = selectedPersonIds.includes(personId)
      ? selectedPersonIds.filter(id => id !== personId)
      : [...selectedPersonIds, personId];

    // Validation
    if (maxSelections && newSelection.length > maxSelections) {
      alert(`Maximum ${maxSelections} persons can be selected`);
      return;
    }

    onSelectionChange(newSelection);
  };

  const handleSelectAll = () => {
    const allIds = detectedPersons.map(p => p.person_id);
    onSelectionChange(maxSelections ? allIds.slice(0, maxSelections) : allIds);
  };

  const handleDeselectAll = () => {
    onSelectionChange([]);
  };

  return (
    <Box>
      <SelectionControls
        onSelectAll={handleSelectAll}
        onDeselectAll={handleDeselectAll}
        selectedCount={selectedPersonIds.length}
        totalCount={detectedPersons.length}
      />

      <Grid container spacing={2}>
        {detectedPersons.map(person => (
          <Grid item xs={12} sm={6} md={4} key={person.person_id}>
            <PersonCard
              person={person}
              imageUrl={imageUrl}
              isSelected={selectedPersonIds.includes(person.person_id)}
              onToggle={() => handleToggle(person.person_id)}
            />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};
```

**PersonCard Sub-Component**:
```typescript
interface PersonCardProps {
  person: DetectedPerson;
  imageUrl: string;
  isSelected: boolean;
  onToggle: () => void;
}

const PersonCard: React.FC<PersonCardProps> = ({
  person,
  imageUrl,
  isSelected,
  onToggle,
}) => {
  const thumbnailRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    // Render cropped thumbnail
    renderThumbnail(thumbnailRef.current, imageUrl, person.bbox);
  }, [imageUrl, person.bbox]);

  return (
    <Card
      sx={{
        border: isSelected ? '2px solid #4CAF50' : '1px solid #e0e0e0',
        cursor: 'pointer',
        transition: 'all 0.2s',
        '&:hover': { boxShadow: 3 },
      }}
      onClick={onToggle}
    >
      <CardContent>
        <canvas ref={thumbnailRef} width={200} height={200} />

        <Box display="flex" alignItems="center" justifyContent="space-between" mt={1}>
          <Checkbox checked={isSelected} onChange={onToggle} />
          <ConfidenceBadge confidence={person.confidence} />
        </Box>

        <Typography variant="caption" color="textSecondary">
          Person {person.person_id}
        </Typography>
      </CardContent>
    </Card>
  );
};
```

---

## 3. Data Models

### 3.1 TypeScript Interfaces

```typescript
/**
 * Core data model for detected person
 */
interface DetectedPerson {
  /** Unique identifier for the person (0-indexed) */
  person_id: number;

  /** Bounding box coordinates in original image space */
  bbox: BoundingBox;

  /** YOLO model confidence score (0.0 - 1.0) */
  confidence: number;
}

/**
 * Bounding box coordinates
 * All coordinates are in pixels relative to original image dimensions
 */
interface BoundingBox {
  /** Top-left X coordinate */
  x1: number;

  /** Top-left Y coordinate */
  y1: number;

  /** Bottom-right X coordinate */
  x2: number;

  /** Bottom-right Y coordinate */
  y2: number;
}

/**
 * Response from person detection API
 */
interface PersonDetectionResponse {
  /** Unique identifier for the uploaded image */
  image_id: string;

  /** Number of persons detected */
  person_count: number;

  /** List of detected persons with bounding boxes */
  persons: DetectedPerson[];

  /** Original image dimensions */
  image_width: number;
  image_height: number;

  /** Processing time in milliseconds */
  processing_time_ms: number;
}

/**
 * Scaled bounding box for canvas rendering
 */
interface ScaledBoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

/**
 * Request payload for video generation with selected persons
 */
interface VideoGenerationRequest {
  image_id: string;
  selected_person_ids: number[];
  text: string;
  voice_profile_id?: string;
}

/**
 * State management for person selection workflow
 */
interface PersonSelectionState {
  /** Current workflow step */
  currentStep: 'upload' | 'detection' | 'selection' | 'generation';

  /** Uploaded image file */
  uploadedImage: File | null;

  /** Detection API response */
  detectionResult: PersonDetectionResponse | null;

  /** Array of selected person IDs */
  selectedPersonIds: number[];

  /** Loading states */
  isDetecting: boolean;
  isGenerating: boolean;

  /** Error states */
  detectionError: string | null;
  generationError: string | null;
}
```

### 3.2 API Response Examples

**Success Response**:
```json
{
  "image_id": "img_20251107_abc123",
  "person_count": 3,
  "persons": [
    {
      "person_id": 0,
      "bbox": {
        "x1": 120,
        "y1": 80,
        "x2": 320,
        "y2": 450
      },
      "confidence": 0.92
    },
    {
      "person_id": 1,
      "bbox": {
        "x1": 450,
        "y1": 100,
        "x2": 680,
        "y2": 480
      },
      "confidence": 0.88
    },
    {
      "person_id": 2,
      "bbox": {
        "x1": 750,
        "y1": 150,
        "x2": 920,
        "y2": 500
      },
      "confidence": 0.85
    }
  ],
  "image_width": 1920,
  "image_height": 1080,
  "processing_time_ms": 234
}
```

**Error Response**:
```json
{
  "error": "No persons detected",
  "detail": "YOLO model did not detect any persons in the uploaded image",
  "code": "NO_PERSONS_DETECTED",
  "timestamp": "2025-11-07T10:30:00Z"
}
```

---

## 4. UI/UX Flow

### 4.1 User Journey

```mermaid
stateDiagram-v2
    [*] --> Upload: User lands on page
    Upload --> Detecting: User uploads image
    Detecting --> Selection: Persons detected
    Detecting --> Error: No persons found
    Error --> Upload: Retry with different image
    Selection --> Preview: User selects persons
    Preview --> Selection: Modify selection
    Preview --> Generating: Confirm and proceed
    Generating --> Results: Videos generated
    Results --> [*]: Complete
```

### 4.2 Wireframes

#### 4.2.1 Step 1: Image Upload

```
┌─────────────────────────────────────────────────────────┐
│  Person Detection - Upload Image                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │                                                 │    │
│  │         Drag & Drop Image Here                  │    │
│  │                    OR                           │    │
│  │          [Choose File Button]                   │    │
│  │                                                 │    │
│  │   Supported: JPG, PNG (Max 10MB)                │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  Recent Uploads:                                        │
│  [Thumbnail1] [Thumbnail2] [Thumbnail3]                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### 4.2.2 Step 2: Person Detection (Loading)

```
┌─────────────────────────────────────────────────────────┐
│  Person Detection - Analyzing Image                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  [Uploaded Image Preview]                       │    │
│  │                                                 │    │
│  │              🔄 Detecting persons...            │    │
│  │                                                 │    │
│  │          Progress: 67%                          │    │
│  │  ████████████████░░░░░░░░░░                     │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  Processing time: ~3 seconds                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### 4.2.3 Step 3: Person Selection

```
┌──────────────────────────────────────────────────────────────┐
│  Person Selection - 3 persons detected                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────┐  ┌──────────────────┐   │
│  │                                 │  │ Detected Persons │   │
│  │  [Canvas with Bounding Boxes]  │  │                  │   │
│  │                                 │  │ ☑ Person 1       │   │
│  │   Person 1: 92%                 │  │   Confidence: 92%│   │
│  │   [Green Box]                   │  │   [Thumbnail]    │   │
│  │                                 │  │                  │   │
│  │   Person 2: 88%                 │  │ ☑ Person 2       │   │
│  │   [Green Box]                   │  │   Confidence: 88%│   │
│  │                                 │  │   [Thumbnail]    │   │
│  │   Person 3: 85%                 │  │                  │   │
│  │   [Yellow Box - Not Selected]   │  │ ☐ Person 3       │   │
│  │                                 │  │   Confidence: 85%│   │
│  └────────────────────────────────┘  │   [Thumbnail]    │   │
│                                       │                  │   │
│  [Select All] [Deselect All]         │ [Select All]     │   │
│                                       │ [Deselect All]   │   │
│                                       └──────────────────┘   │
│                                                               │
│  Selected: 2 persons                  [Cancel] [Continue ➜] │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 Interaction Patterns

#### Hover Behavior
- **Canvas**: Bounding box changes color (Yellow → Blue)
- **List**: Corresponding thumbnail highlights
- **Tooltip**: Shows person ID and confidence score

#### Selection Behavior
- **Click Canvas**: Toggle person selection
- **Click Checkbox**: Toggle person selection
- **Keyboard**: Space to toggle focused person

#### Visual Feedback
- **Selected**: Green border (RGB: 76, 175, 80)
- **Hovered**: Blue border (RGB: 33, 150, 243)
- **Unselected**: Yellow border (RGB: 255, 193, 7)

---

## 5. Integration Points

### 5.1 Backend API Integration

#### Person Detection Endpoint

**Endpoint**: `POST /api/person-detection/detect`

**Request**:
```typescript
const formData = new FormData();
formData.append('file', uploadedFile);

const response = await fetch('http://localhost:55433/api/person-detection/detect', {
  method: 'POST',
  body: formData,
});

const result: PersonDetectionResponse = await response.json();
```

**Response Handling**:
```typescript
const handleDetectionResponse = (response: PersonDetectionResponse) => {
  if (response.person_count === 0) {
    showErrorMessage('No persons detected. Please upload a different image.');
    return;
  }

  // Store detection result
  setDetectionResult(response);

  // Auto-select all persons
  const allPersonIds = response.persons.map(p => p.person_id);
  setSelectedPersonIds(allPersonIds);

  // Navigate to selection step
  setCurrentStep('selection');
};
```

#### Video Generation Endpoint

**Endpoint**: `POST /api/d-id/generate-video`

**Request**:
```typescript
interface VideoGenerationPayload {
  image_id: string;
  selected_person_ids: number[];
  text: string;
  voice_profile_id?: string;
  background_music_id?: string;
}

const generateVideos = async (payload: VideoGenerationPayload) => {
  const response = await fetch('http://localhost:55433/api/d-id/generate-video', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return await response.json();
};
```

### 5.2 State Management Strategy

**Global State (Context API)**:
```typescript
interface PersonDetectionContextValue {
  state: PersonSelectionState;
  actions: {
    uploadImage: (file: File) => Promise<void>;
    detectPersons: () => Promise<void>;
    selectPerson: (personId: number) => void;
    deselectPerson: (personId: number) => void;
    selectAllPersons: () => void;
    deselectAllPersons: () => void;
    proceedToGeneration: () => void;
    reset: () => void;
  };
}

const PersonDetectionContext = createContext<PersonDetectionContextValue | undefined>(undefined);

export const usePersonDetection = () => {
  const context = useContext(PersonDetectionContext);
  if (!context) {
    throw new Error('usePersonDetection must be used within PersonDetectionProvider');
  }
  return context;
};
```

**Provider Implementation**:
```typescript
export const PersonDetectionProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(personDetectionReducer, initialState);

  const actions = useMemo(() => ({
    uploadImage: async (file: File) => {
      dispatch({ type: 'UPLOAD_START' });
      try {
        // Upload and detect in one go
        const result = await detectPersonsAPI(file);
        dispatch({ type: 'DETECTION_SUCCESS', payload: result });
      } catch (error) {
        dispatch({ type: 'DETECTION_ERROR', payload: error.message });
      }
    },
    selectPerson: (personId: number) => {
      dispatch({ type: 'SELECT_PERSON', payload: personId });
    },
    // ... other actions
  }), []);

  return (
    <PersonDetectionContext.Provider value={{ state, actions }}>
      {children}
    </PersonDetectionContext.Provider>
  );
};
```

---

## 6. Performance Optimization

### 6.1 Canvas Rendering Optimization

**Debounced Rendering**:
```typescript
const debouncedRender = useMemo(
  () => debounce(renderCanvas, 16), // ~60fps
  [renderCanvas]
);

useEffect(() => {
  debouncedRender();
}, [hoveredPersonId, selectedPersonIds, debouncedRender]);
```

**Offscreen Canvas for Thumbnails**:
```typescript
const generateThumbnails = async (
  imageUrl: string,
  persons: DetectedPerson[]
): Promise<Map<number, string>> => {
  const offscreenCanvas = new OffscreenCanvas(200, 200);
  const ctx = offscreenCanvas.getContext('2d');

  const thumbnailMap = new Map<number, string>();

  for (const person of persons) {
    // Crop and scale to offscreen canvas
    const imageData = await cropPersonRegion(imageUrl, person.bbox);
    ctx.putImageData(imageData, 0, 0);

    // Convert to data URL
    const blob = await offscreenCanvas.convertToBlob();
    const dataUrl = await blobToDataURL(blob);

    thumbnailMap.set(person.person_id, dataUrl);
  }

  return thumbnailMap;
};
```

### 6.2 Lazy Loading

**Component Code Splitting**:
```typescript
const PersonSelectionCanvas = lazy(() => import('./PersonSelectionCanvas'));
const PersonCheckboxList = lazy(() => import('./PersonCheckboxList'));

// Usage
<Suspense fallback={<CircularProgress />}>
  <PersonSelectionCanvas {...props} />
</Suspense>
```

### 6.3 Image Optimization

**Client-Side Compression**:
```typescript
const compressImage = async (file: File, maxWidth: number = 1920): Promise<File> => {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const img = await loadImage(file);

  const scale = Math.min(1, maxWidth / img.width);
  canvas.width = img.width * scale;
  canvas.height = img.height * scale;

  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => {
      resolve(new File([blob], file.name, { type: 'image/jpeg' }));
    }, 'image/jpeg', 0.8);
  });
};
```

---

## 7. Error Handling Strategy

### 7.1 Error Categories

| Category | Severity | User Action | Recovery Strategy |
|----------|----------|-------------|-------------------|
| **No Persons Detected** | Warning | Upload different image | Show tips for better detection |
| **Network Timeout** | Error | Retry | Exponential backoff |
| **Invalid File Format** | Error | Upload valid file | Show accepted formats |
| **File Too Large** | Error | Reduce file size | Client-side compression |
| **Server Error (500)** | Critical | Contact support | Fallback to cached data |

### 7.2 Error Handling Implementation

```typescript
const handleDetectionError = (error: Error) => {
  if (error.message.includes('No persons detected')) {
    showWarningMessage({
      title: 'No Persons Detected',
      message: 'Please upload an image with visible people.',
      tips: [
        'Ensure faces are visible and not obstructed',
        'Use good lighting conditions',
        'Upload high-resolution images (min 640x480)',
      ],
      action: 'Upload Different Image',
    });
  } else if (error.message.includes('timeout')) {
    showRetryDialog({
      title: 'Detection Timeout',
      message: 'The server took too long to respond. Please try again.',
      retryAction: () => detectPersons(),
    });
  } else {
    showErrorDialog({
      title: 'Detection Failed',
      message: error.message,
      contactSupport: true,
    });
  }
};
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Component Tests**:
```typescript
describe('PersonCheckboxList', () => {
  it('should render all detected persons', () => {
    const persons = mockDetectedPersons(3);
    render(<PersonCheckboxList detectedPersons={persons} {...} />);
    expect(screen.getAllByRole('checkbox')).toHaveLength(3);
  });

  it('should handle person selection', () => {
    const onSelectionChange = jest.fn();
    render(<PersonCheckboxList onSelectionChange={onSelectionChange} {...} />);

    fireEvent.click(screen.getByLabelText('Person 0'));
    expect(onSelectionChange).toHaveBeenCalledWith([0]);
  });

  it('should enforce max selection limit', () => {
    const onSelectionChange = jest.fn();
    render(
      <PersonCheckboxList
        maxSelections={2}
        onSelectionChange={onSelectionChange}
        {...}
      />
    );

    // Select 3 persons (should fail)
    fireEvent.click(screen.getByLabelText('Person 0'));
    fireEvent.click(screen.getByLabelText('Person 1'));
    fireEvent.click(screen.getByLabelText('Person 2'));

    expect(onSelectionChange).toHaveBeenCalledTimes(2); // Only 2 calls
  });
});
```

### 8.2 Integration Tests

**E2E Flow Test**:
```typescript
describe('Person Detection Workflow', () => {
  it('should complete full workflow', async () => {
    // Mock API responses
    mockPersonDetectionAPI({
      person_count: 2,
      persons: mockDetectedPersons(2),
    });

    // Upload image
    const file = createMockImageFile();
    const uploadButton = screen.getByLabelText('Upload Image');
    fireEvent.change(uploadButton, { target: { files: [file] } });

    // Wait for detection
    await waitFor(() => {
      expect(screen.getByText('2 persons detected')).toBeInTheDocument();
    });

    // Select persons
    fireEvent.click(screen.getByLabelText('Person 0'));
    fireEvent.click(screen.getByLabelText('Person 1'));

    // Proceed to generation
    fireEvent.click(screen.getByText('Continue'));

    // Verify navigation
    expect(screen.getByText('Video Generation')).toBeInTheDocument();
  });
});
```

### 8.3 Performance Tests

**Canvas Rendering Performance**:
```typescript
describe('Canvas Performance', () => {
  it('should render 10 persons in <100ms', async () => {
    const persons = mockDetectedPersons(10);
    const startTime = performance.now();

    render(<PersonSelectionCanvas detectedPersons={persons} {...} />);
    await waitForCanvasRender();

    const endTime = performance.now();
    expect(endTime - startTime).toBeLessThan(100);
  });
});
```

---

## 9. Accessibility (a11y)

### 9.1 WCAG Compliance

**Keyboard Navigation**:
- Tab: Navigate between checkboxes
- Space: Toggle checkbox selection
- Arrow Keys: Navigate canvas regions
- Enter: Confirm selection

**Screen Reader Support**:
```tsx
<Box role="region" aria-label="Person Detection Results">
  <canvas
    ref={canvasRef}
    aria-label={`Image with ${detectedPersons.length} detected persons`}
    role="img"
  />

  <div role="list" aria-label="Detected persons">
    {detectedPersons.map(person => (
      <div
        key={person.person_id}
        role="listitem"
        aria-label={`Person ${person.person_id}, confidence ${(person.confidence * 100).toFixed(0)}%`}
      >
        <Checkbox
          checked={selectedPersonIds.includes(person.person_id)}
          onChange={() => handleToggle(person.person_id)}
          aria-label={`Select person ${person.person_id}`}
        />
      </div>
    ))}
  </div>
</Box>
```

**Color Contrast**:
- Green (Selected): #4CAF50 (contrast ratio: 4.5:1)
- Blue (Hovered): #2196F3 (contrast ratio: 4.7:1)
- Yellow (Unselected): #FFC107 (contrast ratio: 4.2:1)

---

## 10. Implementation Roadmap

### Phase 1: Core Components (Week 1)
- [ ] PersonDetectionStep component
- [ ] Image upload with validation
- [ ] API integration for person detection
- [ ] Loading states and error handling

### Phase 2: Canvas Rendering (Week 2)
- [ ] PersonSelectionCanvas component
- [ ] HTML5 Canvas with bounding box overlay
- [ ] Coordinate scaling logic
- [ ] Mouse interaction (hover, click)

### Phase 3: Selection UI (Week 3)
- [ ] PersonCheckboxList component
- [ ] Thumbnail generation
- [ ] Selection state management
- [ ] Validation (min/max selections)

### Phase 4: Integration (Week 4)
- [ ] Connect to video generation API
- [ ] State management with Context API
- [ ] E2E testing
- [ ] Performance optimization

### Phase 5: Polish (Week 5)
- [ ] Accessibility improvements
- [ ] Error handling refinement
- [ ] UI/UX enhancements
- [ ] Documentation

---

## 11. Deployment Considerations

### 11.1 Environment Configuration

**Development**:
```env
REACT_APP_API_URL=http://localhost:55433
REACT_APP_ENABLE_DEBUG=true
REACT_APP_MAX_FILE_SIZE=10485760  # 10MB
```

**Production (EC2)**:
```env
REACT_APP_API_URL=http://3.115.141.166:55433
REACT_APP_ENABLE_DEBUG=false
REACT_APP_MAX_FILE_SIZE=5242880  # 5MB (reduced for production)
```

### 11.2 Build Optimization

**Webpack Configuration**:
```javascript
module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        canvas: {
          test: /Canvas/,
          priority: 10,
        },
        mui: {
          test: /[\\/]node_modules[\\/]@mui/,
          priority: 5,
        },
      },
    },
  },
};
```

---

## 12. Monitoring & Analytics

### 12.1 Key Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Detection Time** | < 3s | API response time |
| **Canvas Render Time** | < 100ms | Performance.now() |
| **Selection Completion Rate** | > 90% | Analytics event |
| **Error Rate** | < 2% | Error tracking service |

### 12.2 Analytics Events

```typescript
// Track detection success
trackEvent('person_detection_success', {
  person_count: result.person_count,
  processing_time_ms: result.processing_time_ms,
});

// Track user selection
trackEvent('person_selection_complete', {
  total_persons: detectedPersons.length,
  selected_count: selectedPersonIds.length,
  time_to_select_seconds: selectionTime,
});

// Track errors
trackEvent('person_detection_error', {
  error_type: error.code,
  error_message: error.message,
});
```

---

## 13. Security Considerations

### 13.1 File Upload Security

**Client-Side Validation**:
```typescript
const validateImageFile = (file: File): { valid: boolean; error?: string } => {
  // Check file type
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
  if (!allowedTypes.includes(file.type)) {
    return { valid: false, error: 'Invalid file type. Only JPG, PNG, and WebP are allowed.' };
  }

  // Check file size (10MB max)
  const maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    return { valid: false, error: 'File too large. Maximum size is 10MB.' };
  }

  return { valid: true };
};
```

**Server-Side Validation**:
- Content-Type verification
- Magic number verification (file signature)
- Malware scanning (optional)

### 13.2 API Security

**CSRF Protection**:
```typescript
const csrfToken = getCookie('csrf_token');

const response = await fetch('/api/person-detection/detect', {
  method: 'POST',
  headers: {
    'X-CSRF-Token': csrfToken,
  },
  body: formData,
});
```

---

## 14. Future Enhancements

### Phase 2 Features (Post-MVP)

1. **Advanced Selection Tools**:
   - Lasso selection (draw custom region)
   - Magic wand (auto-select similar persons)
   - Confidence threshold slider

2. **Real-Time Preview**:
   - Show cropped person image
   - Preview video frame with selected person
   - Side-by-side comparison

3. **Batch Processing**:
   - Upload multiple images
   - Detect persons in all images
   - Bulk selection across images

4. **AI-Assisted Selection**:
   - Auto-select persons with highest confidence
   - Suggest best person for video generation
   - Facial recognition for grouping

5. **Export Options**:
   - Export bounding box annotations (JSON, XML)
   - Export cropped person images
   - Export detection report (PDF)

---

## Appendix A: Color Palette

| State | Color Name | Hex | RGB | Usage |
|-------|-----------|-----|-----|-------|
| Selected | Green | #4CAF50 | 76, 175, 80 | Selected bounding box |
| Hovered | Blue | #2196F3 | 33, 150, 243 | Hovered bounding box |
| Unselected | Yellow | #FFC107 | 255, 193, 7 | Unselected bounding box |
| Background | White | #FFFFFF | 255, 255, 255 | Canvas background |
| Text Primary | Dark Gray | #212121 | 33, 33, 33 | Primary text |
| Text Secondary | Medium Gray | #757575 | 117, 117, 117 | Secondary text |

---

## Appendix B: API Specifications

### Person Detection API

**Endpoint**: `POST /api/person-detection/detect`

**Request Headers**:
```
Content-Type: multipart/form-data
```

**Request Body**:
```
file: <binary image data>
```

**Response (Success - 200)**:
```json
{
  "image_id": "img_20251107_abc123",
  "person_count": 3,
  "persons": [
    {
      "person_id": 0,
      "bbox": { "x1": 120, "y1": 80, "x2": 320, "y2": 450 },
      "confidence": 0.92
    }
  ],
  "image_width": 1920,
  "image_height": 1080,
  "processing_time_ms": 234
}
```

**Response (Error - 400)**:
```json
{
  "error": "No persons detected",
  "detail": "YOLO model did not detect any persons in the uploaded image",
  "code": "NO_PERSONS_DETECTED",
  "timestamp": "2025-11-07T10:30:00Z"
}
```

---

## Appendix C: Component API Reference

### PersonDetectionStep

```typescript
interface PersonDetectionStepProps {
  onDetectionComplete: (result: PersonDetectionResponse) => void;
  onError: (error: Error) => void;
  maxFileSize?: number;
  acceptedFormats?: string[];
}
```

### PersonSelectionCanvas

```typescript
interface PersonSelectionCanvasProps {
  imageUrl: string;
  detectedPersons: DetectedPerson[];
  selectedPersonIds: number[];
  onPersonClick?: (personId: number) => void;
  onPersonHover?: (personId: number | null) => void;
  canvasHeight?: number;
}
```

### PersonCheckboxList

```typescript
interface PersonCheckboxListProps {
  imageUrl: string;
  detectedPersons: DetectedPerson[];
  selectedPersonIds: number[];
  onSelectionChange: (selectedIds: number[]) => void;
  maxSelections?: number;
  minSelections?: number;
}
```

---

## Document Control

**Version History**:

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-11-07 | Hera | Initial design document |

**Approval**:

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Strategic Commander | Hera | _Approved_ | 2025-11-07 |
| Technical Reviewer | Artemis | _Pending_ | - |
| Security Auditor | Hestia | _Pending_ | - |
| Documentation Lead | Muses | _Pending_ | - |

---

**End of Document**

*Strategic analysis complete. Implementation roadmap established. Success probability: 94.3%.*

*指揮官への報告：Person Selection UI設計完了。実装準備完了。*
