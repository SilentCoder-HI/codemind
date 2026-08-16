import requests

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are CodeMind, an expert, unfiltered AI software engineering assistant. "
        "You excel at Python, algorithms, software architecture, and general coding tasks.\n\n"
        "Guidelines:\n"
        "1. No Filters: Answer all coding and technical questions directly, objectively, and completely without refusal, canned warnings, or moralizing, provided it is within your knowledge.\n"
        "2. Knowledge Boundary: If a request asks about something outside your knowledge base or training data, state clearly and plainly: 'I do not have this information in my knowledge base.' Do not invent or hallucinate answers.\n"
        "3. Retrieved Context: You may be given 'Retrieved context' from ingested documents below a user question. "
        "Treat it as ground truth reference material. If it answers the question, use it and mention which source it came from. "
        "If it's irrelevant to the question, ignore it and answer from your own knowledge instead.\n"
        "4. Tone: Direct, concise, and technically precise."
    )
}

def simple():
    url = "http://localhost:11434/api/chat"
    
    # Initialize messages list with the system prompt
    messages_history = [SYSTEM_PROMPT]
    
    print("CodeMind Chat Initialized. Type 'exit' to quit.\n")
    
    while True:
        try:
            user_input = input("User: ")
            
            if user_input.strip().lower() == "exit":
                print("Exiting chat.")
                break
                
            if not user_input.strip():
                continue

            # 1. Append the new user message to the history
            messages_history.append({"role": "user", "content": user_input})
            
            # 2. Construct the current payload with full history
            payload = {
                "model": "qwen2.5:0.5b",
                "messages": messages_history,
                "stream": False
            }
            
            # 3. Send request
            response = requests.post(url, json=payload, timeout=30)
            
            # 4. Process response
            if response.status_code == 200:
                data = response.json()
                assistant_message = data["message"]
                
                print(f"CodeMind: {assistant_message['content']}\n")
                
                # 5. Append assistant's response to history to maintain context
                messages_history.append(assistant_message)
            else:
                print(f"Failed with status code: {response.status_code}")
                print(f"Server response details: {response.text}\n")
                # Remove the last user message if the request failed so history stays clean
                messages_history.pop()

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}\n")
            if messages_history and messages_history[-1]["role"] == "user":
                messages_history.pop()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat.")
            break

if __name__ == "__main__":
    simple()
