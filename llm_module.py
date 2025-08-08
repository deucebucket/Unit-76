# llm_module.py
# Version 2.0: Robust Parsing
# This module now uses regular expressions to reliably extract the JSON
# object from the LLM's response, even if it includes extra text.

import requests
import json
import re # Import the regular expression module

class BigBrain:
    """A class to handle communication with the remote LLM server."""

    def __init__(self, api_url="http://100.64.150.78:5001/api/v1/generate"):
        self.api_url = api_url
        print(f"Big Brain module initialized. Target API: {self.api_url}")

    def get_plan(self, prompt):
        """
        Sends a prompt to the LLM and asks for a plan.

        Args:
            prompt (str): The full prompt including the situation and rules.

        Returns:
            dict: A dictionary representing the action plan, or None on error.
        """
        payload = {
            "prompt": prompt,
            "max_context_length": 1024,
            "max_length": 100, # Increased slightly to ensure JSON isn't cut off
            "temperature": 0.2, # Lowered temperature for more predictable, less creative responses
        }

        try:
            print("Contacting Big Brain for a plan...")
            response = requests.post(self.api_url, json=payload, timeout=20) # Added timeout
            response.raise_for_status()

            result_text = response.json()['results'][0]['text']
            print(f"Big Brain raw response received: {result_text}")

            # --- NEW: Use regex to find the JSON block ---
            # This looks for a string that starts with { and ends with }
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)

            if not json_match:
                print("--- ERROR: No JSON object found in the Big Brain's response.")
                return None

            json_string = json_match.group(0)
            print(f"Extracted JSON: {json_string}")

            plan = json.loads(json_string)
            return plan

        except requests.exceptions.RequestException as e:
            print(f"--- ERROR: Could not connect to Big Brain server: {e}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            print(f"--- ERROR: Could not parse plan from Big Brain: {e}")
            return None
