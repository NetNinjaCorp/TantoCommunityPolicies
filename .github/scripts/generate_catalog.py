#!/usr/bin/env python3
import os
import json
import datetime
from pathlib import Path
import semver

def find_latest_version(policy_path):
    """Find the latest version of a policy based on semantic versioning."""
    versions = []
    for file in os.listdir(policy_path):
        if file.endswith('.json') and file.startswith('v'):
            try:
                # Strip the 'v' prefix and '.json' suffix
                version = file[1:-5]
                # Parse version to validate and compare
                semver.parse(version)
                versions.append(version)
            except ValueError:
                continue
    
    if not versions:
        return None
    
    return max(versions, key=lambda v: semver.parse(v))

def generate_catalog():
    """Generate a catalog of all policies and their latest versions."""
    policies_dir = Path('Policies')
    catalog = {
        "policies": []
    }
    
    # Scan through company directories
    for company in policies_dir.iterdir():
        if not company.is_dir() or company.name == '.github':
            continue
            
        # Scan through policy directories
        for policy in company.iterdir():
            if not policy.is_dir():
                continue
                
            latest_version = find_latest_version(policy)
            if not latest_version:
                continue
                
            # Read the latest version's JSON file
            try:
                with open(policy / f'v{latest_version}.json', 'r') as f:
                    policy_data = json.load(f)
                    
                catalog["policies"].append({
                    "company": company.name,
                    "name": policy_data.get("policyName", policy.name),
                    "description": policy_data.get("description", ""),
                    "version": latest_version,
                    "path": f"{company.name}/{policy.name}/v{latest_version}.json"
                })
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error processing {policy}: {e}")
                continue
    
    # Sort policies by company and name
    catalog["policies"].sort(key=lambda x: (x["company"], x["name"]))
    
    # Add metadata
    catalog["metadata"] = {
        "totalPolicies": len(catalog["policies"]),
        "lastUpdated": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    # Write the catalog file
    os.makedirs(policies_dir, exist_ok=True)
    with open(policies_dir / 'latest.json', 'w') as f:
        json.dump(catalog, f, indent=2)

if __name__ == '__main__':
    generate_catalog()