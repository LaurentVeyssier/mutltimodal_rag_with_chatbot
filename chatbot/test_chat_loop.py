import asyncio
from app import chat_loop

async def test_multi_turn():
    print("--- Turn 1 ---")
    history = []
    response1 = await chat_loop("Who are you?", history)
    print(f"Response 1: {response1[:100]}...")
    
    # Simulate Gradio 'messages' format with multimodal content (list of dicts inside content)
    # This matches the error: Value: [{'text': 'tell me about your work?', 'type': 'text'}]
    history.append({"role": "user", "content": [{"text": "Who are you?", "type": "text"}]})
    history.append({"role": "assistant", "content": [{"text": response1, "type": "text"}]})
    
    print("\n--- Turn 2 ---")
    response2 = await chat_loop("Tell me about Lanzarote.", history)
    print(f"Response 2: {response2[:100]}...")
    
    print("\nTest Passed!")

if __name__ == "__main__":
    asyncio.run(test_multi_turn())
