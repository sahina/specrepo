#!/usr/bin/env python3
"""
Example script demonstrating HAR AI processing capabilities.

This script shows how to use the new AI-powered HAR data processor
to analyze HAR files for pattern recognition, sensitive data detection,
data generalization, and type inference.
"""

import json
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.har_ai_processor import HARDataProcessor
from app.services.har_parser import HARParser


def create_sample_har_data():
    """Create sample HAR data for demonstration."""
    return {
        "log": {
            "version": "1.2",
            "creator": {"name": "Example", "version": "1.0"},
            "entries": [
                {
                    "startedDateTime": "2023-12-25T10:30:00.000Z",
                    "time": 150,
                    "request": {
                        "method": "POST",
                        "url": "https://api.stripe.com/v1/customers/cus_1234567890/charges",
                        "headers": [
                            {
                                "name": "Authorization",
                                "value": "Bearer sk_test_1234567890abcdef1234567890abcdef",
                            },
                            {"name": "Content-Type", "value": "application/json"},
                            {"name": "User-Agent", "value": "MyApp/1.0"},
                        ],
                        "postData": {
                            "mimeType": "application/json",
                            "text": json.dumps(
                                {
                                    "amount": 2000,
                                    "currency": "usd",
                                    "customer": "cus_1234567890",
                                    "description": "Payment for order #12345",
                                    "metadata": {
                                        "order_id": "550e8400-e29b-41d4-a716-446655440000",
                                        "customer_email": "customer@example.com",
                                        "phone": "+1-555-123-4567",
                                    },
                                }
                            ),
                        },
                    },
                    "response": {
                        "status": 200,
                        "statusText": "OK",
                        "headers": [
                            {"name": "Content-Type", "value": "application/json"},
                            {"name": "Request-Id", "value": "req_1234567890"},
                        ],
                        "content": {
                            "mimeType": "application/json",
                            "text": json.dumps(
                                {
                                    "id": "ch_1234567890",
                                    "object": "charge",
                                    "amount": 2000,
                                    "currency": "usd",
                                    "customer": "cus_1234567890",
                                    "created": 1640419800,
                                    "description": "Payment for order #12345",
                                    "metadata": {
                                        "order_id": "550e8400-e29b-41d4-a716-446655440000",
                                        "customer_email": "customer@example.com",
                                        "phone": "+1-555-123-4567",
                                    },
                                    "receipt_url": "https://pay.stripe.com/receipts/payment/CAcQARoXChVhY2N0XzFCbEZKcUlxWWlPbkNhUmcQAg",
                                    "api_key": "sk_live_sensitive_key_here",
                                }
                            ),
                        },
                        "bodySize": 500,
                    },
                },
                {
                    "startedDateTime": "2023-12-25T10:31:00.000Z",
                    "time": 75,
                    "request": {
                        "method": "GET",
                        "url": "https://api.example.com/users/123456/profile",
                        "headers": [
                            {
                                "name": "Authorization",
                                "value": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                            },
                            {"name": "Accept", "value": "application/json"},
                        ],
                    },
                    "response": {
                        "status": 200,
                        "statusText": "OK",
                        "headers": [{"name": "Content-Type", "value": "application/json"}],
                        "content": {
                            "mimeType": "application/json",
                            "text": json.dumps(
                                {
                                    "id": "123456",
                                    "uuid": "550e8400-e29b-41d4-a716-446655440000",
                                    "email": "john.doe@example.com",
                                    "name": "John Doe",
                                    "phone": "+1-555-987-6543",
                                    "created_at": "2023-01-15T08:30:00Z",
                                    "last_login": "2023-12-25T10:00:00Z",
                                    "profile_url": "https://example.com/users/123456",
                                    "credit_card": "4111-1111-1111-1111",
                                    "ssn": "123-45-6789",
                                }
                            ),
                        },
                        "bodySize": 300,
                    },
                },
            ],
        }
    }


def print_section_header(title):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def print_subsection_header(title):
    """Print a formatted subsection header."""
    print(f"\n{'-' * 40}")
    print(f" {title}")
    print(f"{'-' * 40}")


def analyze_har_with_ai():
    """Demonstrate HAR AI processing capabilities."""
    print("HAR AI Processing Demonstration")
    print("This example shows how the AI processor analyzes HAR data for:")
    print("- Pattern recognition (emails, UUIDs, dates, etc.)")
    print("- Sensitive data detection (API keys, tokens, PII)")
    print("- Data generalization for mock responses")
    print("- Type inference for API schemas")

    # Create sample data
    har_data = create_sample_har_data()

    # Initialize parsers
    har_parser = HARParser()
    ai_processor = HARDataProcessor()

    print_section_header("1. PARSING HAR DATA")

    # Parse HAR data
    har_content = json.dumps(har_data)
    interactions = har_parser.parse_har_content(har_content)

    print(f"Parsed {len(interactions)} API interactions from HAR data")
    for i, interaction in enumerate(interactions):
        print(f"  {i + 1}. {interaction.request.method} {interaction.request.url}")

    print_section_header("2. AI ANALYSIS RESULTS")

    # Process each interaction with AI
    for i, interaction in enumerate(interactions):
        print_subsection_header(
            f"Interaction {i + 1}: {interaction.request.method} {interaction.request.url}"
        )

        # Process with AI
        analysis = ai_processor.process_har_interaction(interaction)

        # Display results
        print(f"Interaction ID: {analysis['interaction_id']}")

        # Security concerns
        if analysis["security_concerns"]:
            print(f"\n🚨 SECURITY CONCERNS ({len(analysis['security_concerns'])} found):")
            for concern in analysis["security_concerns"]:
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                emoji = severity_emoji.get(concern["severity"], "⚪")
                print(f"  {emoji} {concern['type'].upper()} (Severity: {concern['severity']})")
                print(f"     Count: {concern['count']}")
                print(f"     Locations: {', '.join(concern['locations'])}")
                print(f"     Recommendation: {concern['recommendation']}")
                if concern["examples"]:
                    print(f"     Examples: {', '.join(concern['examples'][:2])}")

        # Detected patterns
        all_patterns = []
        all_patterns.extend(analysis["request_analysis"]["detected_patterns"])
        all_patterns.extend(analysis["response_analysis"]["detected_patterns"])

        if all_patterns:
            print(f"\n🔍 DETECTED PATTERNS ({len(all_patterns)} found):")
            pattern_summary = {}
            for pattern in all_patterns:
                if pattern.pattern_type not in pattern_summary:
                    pattern_summary[pattern.pattern_type] = []
                pattern_summary[pattern.pattern_type].append(pattern.original_value)

            for pattern_type, values in pattern_summary.items():
                print(f"  📋 {pattern_type.upper()}: {len(values)} instances")
                for value in values[:2]:  # Show first 2 examples
                    print(f"     Example: {value}")

        # Generalization suggestions
        if analysis["generalization_suggestions"]:
            print(
                f"\n💡 GENERALIZATION SUGGESTIONS ({len(analysis['generalization_suggestions'])} found):"
            )
            for suggestion in analysis["generalization_suggestions"]:
                print(f"  🔧 {suggestion['type'].replace('_', ' ').title()}")
                print(f"     Description: {suggestion['description']}")
                if "original_url" in suggestion:
                    print(f"     Original: {suggestion['original_url']}")
                    print(f"     Suggested: {suggestion['suggested_url']}")
                if "patterns_found" in suggestion:
                    print(f"     Patterns: {', '.join(suggestion['patterns_found'])}")

        # Type inference examples
        request_types = analysis["request_analysis"].get("inferred_types", {})
        response_types = analysis["response_analysis"].get("inferred_types", {})

        if request_types or response_types:
            print(f"\n📊 TYPE INFERENCE:")
            if request_types.get("body"):
                print(f"  Request Body Type: {request_types['body']['type']}")
                if "properties" in request_types["body"]:
                    prop_count = len(request_types["body"]["properties"])
                    print(f"    Properties: {prop_count} fields detected")

            if response_types.get("body"):
                print(f"  Response Body Type: {response_types['body']['type']}")
                if "properties" in response_types["body"]:
                    prop_count = len(response_types["body"]["properties"])
                    print(f"    Properties: {prop_count} fields detected")

    print_section_header("3. SUMMARY")

    # Overall summary
    total_security_concerns = sum(
        len(ai_processor.process_har_interaction(interaction)["security_concerns"])
        for interaction in interactions
    )
    total_patterns = sum(
        len(
            ai_processor.process_har_interaction(interaction)["request_analysis"][
                "detected_patterns"
            ]
        )
        + len(
            ai_processor.process_har_interaction(interaction)["response_analysis"][
                "detected_patterns"
            ]
        )
        for interaction in interactions
    )
    total_suggestions = sum(
        len(ai_processor.process_har_interaction(interaction)["generalization_suggestions"])
        for interaction in interactions
    )

    print(f"📈 Analysis Summary:")
    print(f"  • Interactions processed: {len(interactions)}")
    print(f"  • Security concerns found: {total_security_concerns}")
    print(f"  • Data patterns detected: {total_patterns}")
    print(f"  • Generalization suggestions: {total_suggestions}")

    print(f"\n✅ AI processing complete! The system successfully:")
    print(f"  • Identified sensitive data that should be masked or removed")
    print(f"  • Detected data patterns for better type inference")
    print(f"  • Suggested generalizations for reusable mock responses")
    print(f"  • Inferred appropriate data types for OpenAPI schemas")

    print(f"\n💡 Next steps:")
    print(f"  • Review and act on security concerns")
    print(f"  • Apply generalization suggestions to create better mocks")
    print(f"  • Use type inference results for OpenAPI generation")
    print(f"  • Integrate with existing HAR-to-OpenAPI and HAR-to-WireMock workflows")


if __name__ == "__main__":
    try:
        analyze_har_with_ai()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
