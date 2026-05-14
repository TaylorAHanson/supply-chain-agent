import os
import requests
import time

def create_or_update_ab_test_route():
    """
    Creates or updates an AI Gateway route (Model Serving Endpoint) with A/B testing configured.
    It splits traffic 80% to Claude 3.5 Sonnet and 20% to Llama 3 70B for testing.
    """
    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")
    
    if not host or not token:
        # Try to get from CLI if not set
        import subprocess
        import json
        try:
            profile = os.environ.get("DATABRICKS_PROFILE", "myenv")
            host_out = subprocess.check_output(f"databricks auth describe --profile {profile} | grep 'host:' | awk '{{print $3}}'", shell=True)
            host = host_out.decode('utf-8').strip()
            token_out = subprocess.check_output(f"databricks auth token --profile {profile}", shell=True)
            token = json.loads(token_out.decode('utf-8')).get("access_token")
        except Exception as e:
            print(f"Error getting auth from CLI: {e}")
            return
            
    endpoint_name = "supply_chain_agent_endpoint"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": endpoint_name,
        "config": {
            "served_entities": [
                {
                    "name": "target_a_claude",
                    "external_model": {
                        "name": "databricks-claude-sonnet-4-6",
                        "provider": "databricks-model-serving",
                        "task": "llm/v1/chat",
                        "databricks_model_serving_config": {
                            "databricks_workspace_url": host,
                            "databricks_api_token_plaintext": token
                        }
                    }
                },
                {
                    "name": "target_b_llama",
                    "external_model": {
                        "name": "databricks-meta-llama-3-1-8b-instruct",
                        "provider": "databricks-model-serving",
                        "task": "llm/v1/chat",
                        "databricks_model_serving_config": {
                            "databricks_workspace_url": host,
                            "databricks_api_token_plaintext": token
                        }
                    }
                }
            ],
            "traffic_config": {
                "routes": [
                    {"served_model_name": "target_a_claude", "traffic_percentage": 80},
                    {"served_model_name": "target_b_llama", "traffic_percentage": 20}
                ]
            }
        }
    }
    
    # Check if endpoint exists
    resp = requests.get(f"{host}/api/2.0/serving-endpoints", headers=headers)
    endpoints = [e["name"] for e in resp.json().get("endpoints", [])]
    
    if endpoint_name in endpoints:
        print(f"Updating existing endpoint '{endpoint_name}'...")
        resp = requests.put(f"{host}/api/2.0/serving-endpoints/{endpoint_name}/config", headers=headers, json=payload["config"])
        if resp.status_code != 200:
            print(f"Error updating endpoint: {resp.text}")
    else:
        print(f"Creating new endpoint '{endpoint_name}'...")
        resp = requests.post(f"{host}/api/2.0/serving-endpoints", headers=headers, json=payload)
        if resp.status_code != 200:
            print(f"Error creating endpoint: {resp.text}")
        
    print("A/B testing route configured successfully!")

if __name__ == "__main__":
    create_or_update_ab_test_route()
