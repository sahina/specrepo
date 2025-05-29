#!/usr/bin/env python3
"""
Example script demonstrating HAR to WireMock transformation.

This script shows how to use the HARToWireMockTransformer and HARToWireMockService
to convert HAR data into WireMock stub configurations.
"""

import json
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.har_parser import APIInteraction, APIRequest, APIResponse
from app.services.har_to_wiremock import HARToWireMockService, HARToWireMockTransformer


def create_sample_har_data():
    """Create sample HAR-like data for demonstration."""
    # Sample GET request
    get_request = APIRequest(
        method="GET",
        url="https://api.example.com/users/123",
        domain="api.example.com",
        path="/users/123",
        query_params={"include": ["profile", "settings"]},
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; API-Client/1.0)",
        },
        body=None,
        content_type="application/json",
        timestamp="2023-01-01T12:00:00Z",
    )

    get_response = APIResponse(
        status=200,
        status_text="OK",
        headers={
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-RateLimit-Remaining": "99",
        },
        body=(
            '{"id": 123, "name": "John Doe", "email": "john@example.com", '
            '"created_at": "2023-01-01T10:00:00Z"}'
        ),
        content_type="application/json",
        size=1024,
    )

    get_interaction = APIInteraction(
        request=get_request, response=get_response, duration=150.5, entry_id="entry_1"
    )

    # Sample POST request
    post_request = APIRequest(
        method="POST",
        url="https://api.example.com/users",
        domain="api.example.com",
        path="/users",
        query_params={},
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer abc123token",
        },
        body='{"name": "Jane Smith", "email": "jane@example.com", "role": "admin"}',
        content_type="application/json",
        timestamp="2023-01-01T12:01:00Z",
    )

    post_response = APIResponse(
        status=201,
        status_text="Created",
        headers={
            "Content-Type": "application/json",
            "Location": "/users/124",
            "X-RateLimit-Remaining": "98",
        },
        body=(
            '{"id": 124, "name": "Jane Smith", "email": "jane@example.com", '
            '"role": "admin", "created_at": "2023-01-01T12:01:00Z"}'
        ),
        content_type="application/json",
        size=2048,
    )

    post_interaction = APIInteraction(
        request=post_request, response=post_response, duration=250.0, entry_id="entry_2"
    )

    return [get_interaction, post_interaction]


def demonstrate_basic_transformation():
    """Demonstrate basic HAR to WireMock transformation."""
    print("=== Basic HAR to WireMock Transformation ===")

    # Create sample data
    interactions = create_sample_har_data()
    print(f"Created {len(interactions)} sample HAR interactions")

    # Create transformer with default settings
    transformer = HARToWireMockTransformer()

    # Transform interactions to WireMock stubs
    stubs = transformer.transform_interactions(interactions)
    print(f"Generated {len(stubs)} WireMock stubs")

    # Display the first stub
    if stubs:
        print("\nFirst WireMock stub:")
        stub_dict = {
            "request": stubs[0].request,
            "response": stubs[0].response,
            "metadata": stubs[0].metadata,
        }
        print(json.dumps(stub_dict, indent=2))

    return stubs


def demonstrate_configuration_options():
    """Demonstrate different transformer configuration options."""
    print("\n=== Configuration Options ===")

    interactions = create_sample_har_data()

    # Strict matching mode
    print("\n1. Strict Matching Mode:")
    strict_transformer = HARToWireMockTransformer(
        enable_stateful=False, enable_templating=False, strict_matching=True
    )
    strict_stubs = strict_transformer.transform_interactions(interactions)
    print(f"Generated {len(strict_stubs)} stubs with strict matching")

    # Templating disabled
    print("\n2. Templating Disabled:")
    no_template_transformer = HARToWireMockTransformer(enable_templating=False)
    no_template_stubs = no_template_transformer.transform_interactions(interactions)
    print(f"Generated {len(no_template_stubs)} stubs without templating")

    # Stateful disabled
    print("\n3. Stateful Disabled:")
    no_stateful_transformer = HARToWireMockTransformer(enable_stateful=False)
    no_stateful_stubs = no_stateful_transformer.transform_interactions(interactions)
    print(f"Generated {len(no_stateful_stubs)} stubs without stateful behavior")


def demonstrate_file_export():
    """Demonstrate exporting stubs to files."""
    print("\n=== File Export ===")

    interactions = create_sample_har_data()
    transformer = HARToWireMockTransformer()
    stubs = transformer.transform_interactions(interactions)

    # Create output directory
    output_dir = "example_wiremock_mappings"
    os.makedirs(output_dir, exist_ok=True)

    # Export to files
    created_files = transformer.export_to_files(stubs, output_dir)
    print(f"Exported {len(created_files)} mapping files to {output_dir}/")

    for file_path in created_files:
        print(f"  - {file_path}")

    return output_dir


def demonstrate_service_usage():
    """Demonstrate using the HARToWireMockService."""
    print("\n=== Service Usage ===")

    interactions = create_sample_har_data()

    # Create service (without WireMock client for this example)
    service = HARToWireMockService()

    # Transform to files using service
    result = service.transform_to_files(interactions, "service_example_mappings")

    print(f"Service result: {result['message']}")
    print(f"Files created: {len(result['files_created'])}")

    return result


def demonstrate_base_url_stripping():
    """Demonstrate base URL stripping functionality."""
    print("\n=== Base URL Stripping ===")

    interactions = create_sample_har_data()
    transformer = HARToWireMockTransformer()

    # Transform with base URL stripping
    base_url = "https://api.example.com"
    stubs = transformer.transform_interactions(interactions, base_url=base_url)

    print(f"Base URL: {base_url}")
    print("URL patterns after stripping:")
    for i, stub in enumerate(stubs):
        url_key = "url" if "url" in stub.request else "urlPattern"
        print(f"  Stub {i + 1}: {stub.request[url_key]}")


def main():
    """Run all demonstration examples."""
    print("HAR to WireMock Transformation Examples")
    print("=" * 50)

    try:
        # Basic transformation
        demonstrate_basic_transformation()

        # Configuration options
        demonstrate_configuration_options()

        # File export
        output_dir = demonstrate_file_export()

        # Service usage
        demonstrate_service_usage()

        # Base URL stripping
        demonstrate_base_url_stripping()

        print("\n=== Summary ===")
        print("✅ All examples completed successfully!")
        print(f"✅ Check the '{output_dir}' directory for exported WireMock mappings")
        print("✅ Check the 'service_example_mappings' directory for service-generated mappings")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
