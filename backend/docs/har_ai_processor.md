# HAR AI Processor Documentation

## Overview

The HAR AI Processor is a comprehensive system for analyzing HTTP Archive (HAR) files using artificial intelligence techniques. It implements pattern recognition, sensitive data detection, data generalization, and type inference capabilities to enhance the processing of HAR data for API specification generation and mock creation.

## Features

### 1. Pattern Recognition

- **Email addresses**: Detects and validates email patterns
- **UUIDs**: Identifies UUID v4 format identifiers
- **Phone numbers**: Recognizes various phone number formats
- **Dates**: Detects ISO 8601 dates and simple date formats
- **URLs**: Identifies HTTP/HTTPS URLs
- **IP addresses**: Recognizes IPv4 addresses
- **Numeric IDs**: Detects large numeric identifiers
- **Credit card numbers**: Identifies credit card patterns

### 2. Sensitive Data Detection

- **API keys**: Detects various API key patterns
- **Bearer tokens**: Identifies OAuth bearer tokens
- **JWT tokens**: Recognizes JSON Web Tokens
- **Passwords**: Detects password fields
- **Authorization headers**: Identifies authorization headers
- **Session IDs**: Detects session identifiers
- **Credit card numbers**: Flags credit card data
- **Social Security Numbers**: Identifies SSN patterns

### 3. Data Generalization

- **URL parameterization**: Converts specific IDs to path parameters
- **Response templating**: Creates template variables for dynamic data
- **Header sanitization**: Removes or masks sensitive headers
- **Body generalization**: Replaces specific values with placeholders

### 4. Type Inference

- **OpenAPI schema generation**: Infers appropriate OpenAPI types
- **Format detection**: Identifies string formats (email, uuid, date-time, etc.)
- **Array type inference**: Analyzes array contents for item schemas
- **Object property analysis**: Infers object properties and required fields

## Architecture

### Core Classes

#### `HARDataPatternRecognizer`

Handles pattern detection using regular expressions and confidence scoring.

```python
from app.services.har_ai_processor import HARDataPatternRecognizer

recognizer = HARDataPatternRecognizer()
patterns = recognizer.detect_patterns("Contact: user@example.com")
sensitive = recognizer.detect_sensitive_data("api_key: sk-123456", "header")
```

#### `HARDataGeneralizer`

Processes data to create generalized versions suitable for mock responses.

```python
from app.services.har_ai_processor import HARDataGeneralizer

generalizer = HARDataGeneralizer()
result = generalizer.generalize_json_data({"user_id": "123", "email": "user@example.com"})
```

#### `HARTypeInferencer`

Infers OpenAPI schema types from data values.

```python
from app.services.har_ai_processor import HARTypeInferencer

inferencer = HARTypeInferencer()
schema = inferencer.infer_type({"name": "John", "age": 30, "email": "john@example.com"})
```

#### `HARDataProcessor`

Main coordinator class that orchestrates all AI processing capabilities.

```python
from app.services.har_ai_processor import HARDataProcessor
from app.services.har_parser import HARParser

# Parse HAR file
parser = HARParser()
interactions = parser.parse_har_content(har_content)

# Process with AI
processor = HARDataProcessor()
for interaction in interactions:
    analysis = processor.process_har_interaction(interaction)
```

## Data Structures

### `DataPattern`

Represents a detected data pattern:

```python
@dataclass
class DataPattern:
    pattern_type: str          # Type of pattern (email, uuid, etc.)
    confidence: float          # Confidence score (0.0-1.0)
    original_value: str        # Original detected value
    generalized_value: str     # Suggested replacement/placeholder
    description: str           # Human-readable description
```

### `SensitiveDataMatch`

Represents detected sensitive data:

```python
@dataclass
class SensitiveDataMatch:
    data_type: str             # Type of sensitive data
    location: str              # Where found (header, body, url)
    field_name: str            # Field or header name
    value: str                 # Detected value
    confidence: float          # Detection confidence
    suggested_replacement: str # Recommended replacement
```

### `GeneralizedData`

Contains original and generalized versions of data:

```python
@dataclass
class GeneralizedData:
    original: Any                           # Original data
    generalized: Any                        # Generalized version
    patterns: List[DataPattern]             # Detected patterns
    sensitive_matches: List[SensitiveDataMatch]  # Sensitive data found
```

## Usage Examples

### Basic Pattern Detection

```python
from app.services.har_ai_processor import HARDataPatternRecognizer

recognizer = HARDataPatternRecognizer()

# Detect patterns in text
text = "User ID: 550e8400-e29b-41d4-a716-446655440000, Email: user@example.com"
patterns = recognizer.detect_patterns(text)

for pattern in patterns:
    print(f"Found {pattern.pattern_type}: {pattern.original_value}")
    print(f"Suggested replacement: {pattern.generalized_value}")
    print(f"Confidence: {pattern.confidence}")
```

### Sensitive Data Detection

```python
# Check for sensitive data
header_text = "Authorization: Bearer sk-1234567890abcdef"
sensitive_matches = recognizer.detect_sensitive_data(header_text, "header")

for match in sensitive_matches:
    print(f"⚠️  Found {match.data_type} in {match.location}")
    print(f"Recommendation: {match.suggested_replacement}")
```

### Complete HAR Processing

```python
from app.services.har_parser import HARParser
from app.services.har_ai_processor import HARDataProcessor

# Parse HAR file
parser = HARParser()
interactions = parser.parse_har_content(har_content)

# Process with AI
processor = HARDataProcessor()
for interaction in interactions:
    analysis = processor.process_har_interaction(interaction)
    
    # Security concerns
    for concern in analysis['security_concerns']:
        print(f"Security issue: {concern['type']} (severity: {concern['severity']})")
        print(f"Recommendation: {concern['recommendation']}")
    
    # Generalization suggestions
    for suggestion in analysis['generalization_suggestions']:
        print(f"Suggestion: {suggestion['description']}")
        if 'original_url' in suggestion:
            print(f"  Original: {suggestion['original_url']}")
            print(f"  Suggested: {suggestion['suggested_url']}")
```

## Integration with Existing Services

### HAR to OpenAPI Integration

The AI processor enhances the existing HAR to OpenAPI transformation:

```python
from app.services.har_to_openapi import HARToOpenAPITransformer
from app.services.har_ai_processor import HARDataProcessor

# Enhanced transformation with AI insights
transformer = HARToOpenAPITransformer()
ai_processor = HARDataProcessor()

for interaction in interactions:
    # Get AI analysis
    analysis = ai_processor.process_har_interaction(interaction)
    
    # Use inferred types for better schema generation
    request_schema = analysis['request_analysis']['inferred_types']
    response_schema = analysis['response_analysis']['inferred_types']
    
    # Apply to OpenAPI generation
    openapi_spec = transformer.transform_interaction(interaction, ai_insights=analysis)
```

### HAR to WireMock Integration

The AI processor improves WireMock stub generation:

```python
from app.services.har_to_wiremock import HARToWireMockTransformer
from app.services.har_ai_processor import HARDataProcessor

transformer = HARToWireMockTransformer()
ai_processor = HARDataProcessor()

for interaction in interactions:
    # Get AI analysis
    analysis = ai_processor.process_har_interaction(interaction)
    
    # Use generalized data for better mocks
    generalized_request = analysis['request_analysis']['body_analysis']
    generalized_response = analysis['response_analysis']['body_analysis']
    
    # Create enhanced WireMock stubs
    stub = transformer.create_stub(interaction, ai_insights=analysis)
```

## Configuration

### Pattern Confidence Thresholds

You can adjust confidence thresholds for different pattern types:

```python
recognizer = HARDataPatternRecognizer()

# Patterns with high confidence (0.9+): UUID, JWT tokens
# Patterns with medium confidence (0.7-0.8): Email, API keys
# Patterns with lower confidence (0.6): Numeric IDs
```

### Sensitive Data Categories

The system categorizes sensitive data by severity:

- **High severity**: Passwords, credit cards, SSNs, API keys
- **Medium severity**: Bearer tokens, JWT tokens, authorization headers
- **Low severity**: Session IDs, other potentially sensitive patterns

## Testing

The AI processor includes comprehensive tests:

```bash
# Run all AI processor tests
uv run pytest tests/test_har_ai_processor.py -v

# Run specific test categories
uv run pytest tests/test_har_ai_processor.py::TestHARDataPatternRecognizer -v
uv run pytest tests/test_har_ai_processor.py::TestHARDataGeneralizer -v
uv run pytest tests/test_har_ai_processor.py::TestHARTypeInferencer -v

# Run integration tests
uv run pytest tests/test_har_ai_processor.py -m integration -v
```

## Example Output

When processing a HAR file, the AI processor provides structured analysis:

```json
{
  "interaction_id": "entry_1",
  "request_analysis": {
    "url_analysis": {
      "original": "https://api.example.com/users/123456",
      "generalized": "https://api.example.com/users/{id}",
      "patterns": [...],
      "sensitive_matches": [...]
    },
    "headers_analysis": {...},
    "body_analysis": {...},
    "sensitive_data": [...],
    "detected_patterns": [...],
    "inferred_types": {...}
  },
  "response_analysis": {...},
  "generalization_suggestions": [
    {
      "type": "url_parameterization",
      "description": "Convert specific URL values to path parameters",
      "original_url": "https://api.example.com/users/123456",
      "suggested_url": "https://api.example.com/users/{id}",
      "patterns_found": ["numeric_id"]
    }
  ],
  "security_concerns": [
    {
      "type": "api_key",
      "severity": "high",
      "count": 1,
      "locations": ["header"],
      "recommendation": "Remove API keys from HAR files and use environment variables",
      "examples": ["x-api-key"]
    }
  ]
}
```

## Performance Considerations

- **Pattern matching**: Uses compiled regex patterns for efficiency
- **Confidence scoring**: Lightweight calculations based on pattern characteristics
- **Memory usage**: Processes interactions individually to manage memory
- **Scalability**: Designed to handle large HAR files with many interactions

## Security Best Practices

1. **Never log sensitive data**: The processor identifies but doesn't log sensitive values
2. **Sanitize outputs**: Always review and sanitize AI-generated suggestions
3. **Validate patterns**: Use confidence scores to filter low-quality matches
4. **Secure storage**: Store processed results securely, especially if they contain metadata about sensitive data

## Future Enhancements

- **Machine learning models**: Integration with ML models for better pattern recognition
- **Custom pattern definitions**: User-defined patterns for domain-specific data
- **Advanced type inference**: More sophisticated schema inference using statistical analysis
- **Performance optimization**: Caching and parallel processing for large datasets
- **Integration APIs**: RESTful APIs for external system integration

## Dependencies

- `python-dateutil`: For date parsing and validation
- `re`: For regular expression pattern matching
- `json`: For JSON data processing
- `urllib.parse`: For URL parsing and analysis

## Contributing

When adding new patterns or sensitive data types:

1. Add pattern definitions to the appropriate class constants
2. Implement confidence calculation logic
3. Add comprehensive tests
4. Update documentation with examples
5. Consider security implications of new patterns
