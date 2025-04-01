import openai
import json
import config
from pprint import pprint
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

def test_openai_simple():
    # Initialize client with longer timeout
    client = openai.OpenAI(
        api_key=config.OPENAI_API_KEY,
        timeout=30.0,  # Increase timeout to 30 seconds
        max_retries=3  # Allow 3 retries
    )
    
    print("\nDEBUG - API Request:")
    print("URL: https://api.openai.com/v1/chat/completions")
    print("Method: POST")
    
    # Get the conversation URL from the user
    conversation_url = input("Please enter your public ChatGPT conversation URL: ")
    
    # Test message with reference to the conversation
    messages = [
        {
            "role": "system",
            "content": f"You are continuing the conversation from {conversation_url}. You should evaluate projects and provide scores exactly as established in that conversation. Follow the same scoring criteria and methodology."
        },
        {
            "role": "user",
            "content": "Test project: Python API Development with the following details:\nTitle: Python API Development\nBudget: $500-1000\nDescription: Need an experienced Python developer to create a RESTful API using Flask or FastAPI. The API will handle user authentication, data validation, and integrate with a PostgreSQL database."
        }
    ]
    
    print("\nDEBUG - Request Headers:")
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY[:5]}...[REDACTED]",
        "Content-Type": "application/json"
    }
    pprint(headers)
    
    print("\nDEBUG - Request Body:")
    request_body = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }
    pprint(request_body)
    
    try:
        print("\nSending request to OpenAI...")
        for attempt in range(3):  # Try up to 3 times
            try:
                print(f"\nAttempt {attempt + 1}...")
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
                
                print("\nDEBUG - Response Status: Success")
                print("\nDEBUG - Response Structure:")
                pprint(vars(response))
                
                print("\nDEBUG - Response Content:")
                content = response.choices[0].message.content
                print(content)
                
                # Extract score from response
                print("\nDEBUG - Attempting to extract score...")
                try:
                    # Look for numbers in the response
                    import re
                    scores = re.findall(r'\b([0-9]{1,3})/100\b|\b([0-9]{1,3})\s*points\b|\bscore:\s*([0-9]{1,3})\b|\brating:\s*([0-9]{1,3})\b', content.lower())
                    if scores:
                        # Flatten the list of tuples and remove empty strings
                        scores = [int(s) for t in scores for s in t if s]
                        if scores:
                            print(f"\nExtracted Score: {scores[0]}/100")
                except Exception as e:
                    print(f"Score extraction failed: {str(e)}")
                
                break  # Success, exit the retry loop
                
            except (openai.APITimeoutError, openai.APIError, openai.RateLimitError) as e:
                print(f"\nDEBUG - Error on attempt {attempt + 1}:")
                print(f"Error Type: {type(e).__name__}")
                print(f"Error Message: {str(e)}")
                if attempt == 2:  # Last attempt
                    raise  # Re-raise the error
                print("Retrying...")
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
        
    except (openai.APITimeoutError, openai.APIError, openai.RateLimitError) as e:
        print("\nDEBUG - All attempts failed:")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
    except Exception as e:
        print("\nDEBUG - Error:")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        import traceback
        print("Traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_openai_simple() 