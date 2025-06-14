import openai
import config
import json
from pprint import pprint
import time
import os

def test_chat_completions_endpoint():
    """
    Tests the chat completions endpoint by sending a request and showing the response structure
    """
    print("\n===== TESTING CHAT COMPLETIONS ENDPOINT =====")
    print("\nEndpoint: https://api.openai.com/v1/chat/completions")
    print("Purpose: Create new chat completions (not listing past completions)")
    
    try:
        # Initialize client
        client = openai.OpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=30.0
        )
        
        # Create a sample chat completion request
        print("\nSending test request to chat completions endpoint...")
        
        # Define messages for the conversation
        messages = [
            {"role": "system", "content": "You are a helpful assistant that responds with JSON when possible."},
            {"role": "user", "content": "List 3 programming languages as a JSON array with their key features."}
        ]
        
        # Show the request details
        print("\nRequest Details:")
        print("----------------")
        print(f"Model: gpt-3.5-turbo")
        print("Messages:")
        for msg in messages:
            print(f"  - {msg['role']}: {msg['content'][:50]}...")
        
        # Make the API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500
        )
        
        # Show the response
        print("\n✅ API Request Successful!")
        print("\nResponse Structure:")
        print("------------------")
        print(f"ID: {response.id}")
        print(f"Created: {response.created}")
        print(f"Model: {response.model}")
        print(f"System Fingerprint: {response.system_fingerprint}")
        print(f"Choice Count: {len(response.choices)}")
        print(f"Prompt Tokens: {response.usage.prompt_tokens}")
        print(f"Completion Tokens: {response.usage.completion_tokens}")
        print(f"Total Tokens: {response.usage.total_tokens}")
        
        # Display the actual response content
        print("\nResponse Content:")
        print("----------------")
        content = response.choices[0].message.content
        print(content)
        
        print("\nIMPORTANT NOTE:")
        print("The OpenAI API doesn't have an endpoint to list past completions or conversations.")
        print("You can only create new completions and store them yourself if you need to access them later.")
        
    except Exception as e:
        print(f"\n❌ API Request failed:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {str(e)}")
        import traceback
        print(traceback.format_exc())

# Function to save conversation to a file
def save_conversation(messages, completion_id):
    with open("conversation_history.json", "w") as f:
        json.dump({
            "completion_id": completion_id,
            "messages": messages
        }, f)

# Function to load conversation from a file
def load_conversation():
    if os.path.exists("conversation_history.json"):
        with open("conversation_history.json", "r") as f:
            data = json.load(f)
            return data.get("messages", [])
    return [{"role": "system", "content": "You are a helpful assistant."}]

def continue_conversation():
    # Initialize client
    client = openai.OpenAI(
        api_key=config.OPENAI_API_KEY,
        timeout=30.0
    )
    
    # Load previous messages
    messages = load_conversation()
    
    # Get new user input
    user_input = input("Your message: ")
    messages.append({"role": "user", "content": user_input})
    
    # Make the API call
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=500
    )
    
    # Add assistant's response to the conversation
    assistant_response = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_response})
    
    # Save the updated conversation
    save_conversation(messages, response.id)
    
    # Display the response
    print(f"\nAssistant: {assistant_response}")

def load_vyftec_context():
    """Load the vyftec context from the markdown file"""
    context_file = "vyftec-context.md"
    if os.path.exists(context_file):
        with open(context_file, "r", encoding="utf-8") as f:
            return f.read()
    else:
        print(f"Warning: {context_file} not found. Using default context.")
        return """
        Vyftec is a premium web agency based in Zug, Switzerland, specializing in:
        1. Corporate websites using WordPress and Redaxo
        2. Backends and dashboards with Laravel
        3. Financial applications including trading algorithms and payment gateway integrations
        """

def save_evaluation(project, evaluation, completion_id):
    """Save the project evaluation to a file"""
    evaluations_file = "project_evaluations.json"
    
    # Load existing evaluations if the file exists
    if os.path.exists(evaluations_file):
        with open(evaluations_file, "r") as f:
            evaluations = json.load(f)
    else:
        evaluations = []
    
    # Add new evaluation
    current_time = int(time.time())
    evaluations.append({
        "completion_id": completion_id,
        "timestamp": current_time,
        "project": project[:200] + "...",  # First 200 chars of project
        "evaluation": evaluation
    })
    
    # Save updated evaluations
    with open(evaluations_file, "w") as f:
        json.dump(evaluations, f, indent=2)
    
    print(f"\nEvaluation saved with ID: {completion_id}")

def evaluate_project(project_description):
    """
    Create a new completion that references the previous conversation and evaluates a project
    using the full vyftec context
    """
    print("\n===== PROJECT EVALUATION WITH FULL CONTEXT =====")
    
    try:
        # Initialize client
        client = openai.OpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=60.0  # Longer timeout for larger context
        )
        
        # Load the full vyftec context
        vyftec_context = load_vyftec_context()
        
        # Create system message that includes the full context
        system_message = """
        You are evaluating projects for vyftec.com based on how well they match the company's capabilities.
        
        Below is the full context about vyftec to use for your evaluation:
        
        """ + vyftec_context + """
        
        Your task is to evaluate the project on a scale of 1-100 based on how well it matches vyftec's capabilities.
        Provide a score and a brief explanation for your rating.
        Format your response as:
        
        Score: [1-100]
        
        Explanation: [Your detailed assessment]
        """
        
        # Send the project description for evaluation
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Please evaluate this project for vyftec:\n\n{project_description}"}
        ]
        
        print("Sending request to OpenAI with full context...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500
        )
        
        # Display the evaluation result
        print("\nProject Evaluation Result:")
        print("-------------------------")
        evaluation = response.choices[0].message.content
        print(evaluation)
        
        # Save the evaluation
        save_evaluation(project_description, evaluation, response.id)
        
        return evaluation
        
    except Exception as e:
        print(f"\n❌ API Request failed:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    # Project to evaluate - you can replace this with any project description
    project_description = """
    We are looking for a talented PHP developer to support the development and maintenance of our e-commerce system. The ideal candidate should have experience with API integrations, database management, and modern frontend technologies. Additionally, a strong understanding of e-commerce logic, particularly around inventory management and order processing, will be highly beneficial.  Responsibilities:  Integrating Shopify Admin API for order imports Working with MySQL databases and migrating product tables Implementing and managing Redis instances for performance optimization Handling XML files and FTP to communicate with our logistics service provider Developing and maintaining CLI commands for recurring tasks Implementing job queues (especially with Redis) to enhance system performance Developing frontend components in a Vite + Vue.js Single Page Application Requirements:  PHP experience (version 8.2) and knowledge of Composer E-commerce experience, particularly with inventory management in online stores Experience with Shopify API and integrating it into existing systems Proficiency in MySQL databases and data migration Experience with Redis for performance optimization Frontend development experience with Vite and Vue.js for SPA development Experience with Job Queue Management in Laravel (specifically with ShouldQueue) Strong communication skills and the ability to understand and implement technical requirements within a team Additional Requirements:  E-commerce background is a must. The candidate should be familiar with the logic and processes of inventory management and order processing to ensure seamless integration across systems. Understanding the logic behind inventory and order processes, and their implementation, is crucial for successfully integrating and evolving the existing systems.
    """
    
    evaluate_project(project_description)