#!/usr/bin/env python3
import os
import json
import msgpack
from pathlib import Path
import sys
from typing import Dict, Any
from jsonschema import validate

# Define the schema for a settings object that can contain nested settings
SETTINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "settingType": {"type": "string"},
        "sequence": {"type": "integer"},
        "required": {"type": "boolean"},
        "enabled": {"type": "boolean"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "hive": {"type": "string"},
        "keyPath": {"type": "string"},
        "valueName": {"type": "string"},
        "valueType": {"type": "string"},
        "value": {"type": ["string", "integer"]},
        "operation": {"type": "string"},
        "direction": {"type": "string"},
        "action": {"type": "string"},
        "category": {"type": "string"},
        "requiresReboot": {"type": "boolean"},
        "protocol": {
            "type": "array",
            "items": {"type": "string"}
        },
        "remoteAddress": {
            "type": "array",
            "items": {"type": "string"}
        },
        "settings": {
            "type": "array",
            "items": {"$ref": "#/definitions/setting"}
        }
    }
}

# Define the expected schema for Tanto policies
POLICY_SCHEMA = {
    "type": "object",
    "required": ["policyName", "description", "version", "createdDate", "modifiedDate", "author", "policies"],
    "definitions": {
        "setting": SETTINGS_SCHEMA
    },
    "properties": {
        "policyName": {"type": "string"},
        "description": {"type": "string"},
        "version": {"type": "string"},
        "createdDate": {"type": "string", "format": "date-time"},
        "modifiedDate": {"type": "string", "format": "date-time"},
        "author": {"type": "string"},
        "configuration": {
            "oneOf": [
                {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "required": ["name", "description", "defaultValue", "dataType"],
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "defaultValue": {"type": "string"},
                            "dataType": {"type": "string", "enum": ["string", "int", "bool"]},
                            "required": {"type": "boolean"},
                            "validationRegex": {"type": "string"},
                            "minValue": {"type": "string"},
                            "maxValue": {"type": "string"},
                            "allowedValues": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
                }
            ]
        },
        "policies": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "description", "enabled", "category", "settings"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "enabled": {"type": "boolean"},
                    "category": {"type": "string"},
                    "requiresReboot": {"type": "boolean"},
                    "settings": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/setting"}
                    }
                }
            }
        }
    }
}

def compress_msgpack(data):
    """Compress data using MessagePack with highest compression level."""
    return msgpack.packb(data, use_bin_type=True)

def validate_policy(data: Dict[str, Any], file_path: str) -> bool:
    """Validate the policy data against the schema."""
    # Skip validation for latest.json
    if file_path.endswith('latest.json'):
        return True
        
    try:
        validate(instance=data, schema=POLICY_SCHEMA)
        return True
    except Exception as e:
        print(f"❌ Validation error in {file_path}: {str(e)}")
        return False

def get_changed_files():
    """Get list of JSON files changed in the latest commit."""
    try:
        # If running in GitHub Actions
        if os.environ.get('GITHUB_EVENT_NAME') == 'push':
            import subprocess
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD^', 'HEAD'],
                capture_output=True,
                text=True
            )
            files = result.stdout.splitlines()
            return [f for f in files if f.endswith('.json') and f.startswith('Policies/')]
    except Exception as e:
        print(f"Error getting changed files: {e}")
    
    # Fallback: process all JSON files
    json_files = []
    for root, _, files in os.walk('Policies'):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files

def convert_to_msgpack(json_path):
    """Convert a JSON file to MessagePack format after validation."""
    try:
        # Read JSON file
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Validate the policy (will skip for latest.json)
        if not validate_policy(data, json_path):
            return False
        
        # Create MessagePack file path
        msgpack_path = json_path.rsplit('.', 1)[0] + '.msgpack'
        
        # Compress and write MessagePack file
        packed_data = compress_msgpack(data)
        with open(msgpack_path, 'wb') as f:
            f.write(packed_data)
        
        # Verify the packed data by reading it back
        with open(msgpack_path, 'rb') as f:
            unpacked = msgpack.unpackb(f.read(), use_list=True)
            if unpacked != data:
                print(f"❌ Verification failed for {json_path}")
                return False
        
        # Print file size comparison
        json_size = os.path.getsize(json_path)
        msgpack_size = os.path.getsize(msgpack_path)
        compression_ratio = (1 - (msgpack_size / json_size)) * 100
        
        print(f"✅ Converted {json_path} to {msgpack_path}")
        print(f"   📊 Compression: {json_size:,} bytes → {msgpack_size:,} bytes ({compression_ratio:.1f}% smaller)")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {json_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error converting {json_path}: {e}")
        return False

def main():
    """Main function to handle MessagePack conversion."""
    success_count = 0
    error_count = 0
    total_json_size = 0
    total_msgpack_size = 0
    
    # Get files to process
    json_files = get_changed_files()
    
    print(f"🔍 Found {len(json_files)} JSON files to process")
    
    # Process each file
    for json_file in json_files:
        print(f"\n📄 Processing {json_file}")
        if convert_to_msgpack(json_file):
            success_count += 1
            total_json_size += os.path.getsize(json_file)
            total_msgpack_size += os.path.getsize(json_file.rsplit('.', 1)[0] + '.msgpack')
        else:
            error_count += 1
    
    # Print summary
    print("\n📊 Conversion Summary:")
    print(f"✅ Successfully converted: {success_count}")
    print(f"❌ Failed conversions: {error_count}")
    if success_count > 0:
        total_compression = (1 - (total_msgpack_size / total_json_size)) * 100
        print(f"📦 Total size reduction: {total_json_size:,} bytes → {total_msgpack_size:,} bytes")
        print(f"💪 Overall compression ratio: {total_compression:.1f}%")
    
    # Exit with error if any conversions failed
    if error_count > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()