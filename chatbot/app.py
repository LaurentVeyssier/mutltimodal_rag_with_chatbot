import gradio as gr
import os
import sys
import json
import asyncio
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google.generativeai.types import content_types
from collections.abc import Iterable
from rich.console import Console
from rich.markdown import Markdown
console = Console()

# Load environment variables
load_dotenv()

# Configure Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables.")
else:
    genai.configure(api_key=API_KEY)

# Manrique Prompt (Copied for self-containment)
excerpts_1 = """Diálogo de César Manrique
[00:04:52]Bueno, hablar de la naturaleza es algo un poco difícil en un corto espacio de tiempo, no. La naturaleza es algo tan maravilloso y tan milagroso que el hombre tiene que estar en una auténtica investigación para ir descubriendo todos sus secretos.
[00:07:05]No cabe duda que la música forma parte de la gran armonía del viento, del zumbido de las alas de las mariposas, de contemplar las estrellas, todo eso es como musical, y la música es un elemento del arte complementario para el confort de la vida y la armonía de poder escuchar y sentir.
[00:08:47]Bueno, a mí Aretha Franklin me encanta y me encantan, bueno, muchísimas, muchísimos músicos. Yo me acuerdo cuando vivía en Nueva York, me marchaba siempre a Harlem, al Teatro Apollo, a oír a todos los músicos negros que me parecen una maravilla y son los que han...
[00:10:53]Bueno, a mí me, siempre me ha gustado, claro, lo que más me gusta desde que era pequeño es la pintura, pero creo que también la pintura está en un momento de degradación o de, ¿cómo te podría decir yo?, una juventud un poco ansiosa de encontrar algo nuevo y hay algo desesperante en el medio que estamos viviendo a nivel, a nivel cultural de la pintura y yo creo que entonces hay que buscar otros medios. Yo por ejemplo ahora creo que estoy descubriendo una nueva faceta que me parece muy importante ya que los alemanes me la han catalogado.
[00:12:44]Que he realizado un espacio que es verdaderamente espectacular y creo que deben visitarlo porque hay algo que realmente es nuevo en el concepto de aglutinar todas las artes como un espacio armónico para la vida y para el hombre.
[00:13:07]Importante. Entonces me invitaron y estuve precisamente con los ecologistas andaluces y también con los del Gobierno viendo todo, me llevaron a ver qué idea podía tener y claro, yo me quedé muy sorprendido cuando veo aquella llanura inmensa que era como un horizonte horizontal con láminas de agua enorme y pregunté, bueno, aquí no hay piedra, dice, no, no hay piedra, solamente es tierra y agua horizontal. Yo me quedé muy preocupado porque pensé que dije, bueno, sin piedra, acostumbrado a mí es la de Lanzarote que es todo una pura piedra, digo, así que no puedo hacer nada, pero estuve observando largo tiempo las láminas enormes de agua en horizontal absoluto, donde se no se veía sino un horizonte. Y entonces se me ocurrió de repente la idea de crear allí palafitos construidos todos en madera sobre el aire, sobre las láminas de agua. Entonces, los ingenieros que estaban ahí se quedaron tan sorprendidos y me dijeron, César, tú eres un brujo.
[00:15:37]Un gran, un gran científico y un gran ingeniero.
[00:15:53]Hombre, el ballet es una maravilla, no. El ballet te encanta. Me encanta porque es donde el hombre o la mujer adquieren la mayor armonía de movimientos.
[00:17:15]No sé qué decirte porque son tantos que no sé cuál cuál poderte decir el que más me gusta, no, hay muchísimos. Yo me acuerdo que en Nueva York me iba siempre a ver el ballet. En Londres vi una vez a Nureyev y a Margot Fonteyn.
[00:18:24]Ficción. Me tuve que poner zapatos de plástico, me metían en un tubo para poder llegar al centro y cuando vi el efecto, no me lo creía, era tan extraordinariamente plástico de una belleza tan grande que pensé inmediatamente en aplicarlo a la escenografía de la ópera Carmen.
[00:23:01]Muy un poco caótico en el mundo para saber exactamente lo que es realmente consustancial con el sentimiento y el espíritu del hombre. Estamos tratando de huir de esa espiritualidad y creo que es un grave error, no. Porque no cabe duda que el hombre siempre ha tenido una manera de caminar basándose en sus propios sentimientos y en su propia...
[00:25:40]Gracias a vosotros.
"""
excerpts_2 = """Nobody knew the island of Lanzarote, and within the Canary Islands, the island of Lanzarote was like the Cinderella of the Canaries. People would laugh, saying that in Lanzarote there was nothing but camels and stones, and that it was the ugliest island in the entire archipelago. But I, however, had the awareness that Lanzarote was an exceptional island, and of a plastic beauty that people didn't understand. That's why I wanted to return and put it on display, like putting a mat, a frame around it, so that people would realize the great plastic and beautiful power of the island, and I have been able to achieve it. People have been able to perfectly understand the enormous beauty of a stone, of a, of a tunera (prickly pear cactus), right down to the beauty of a camel, or the beauty of a farmer plowing the land, or even its popular architecture that was being scorned and totally misunderstood. When they believed it was old, ugly, and anti-functional, they were homes that were perfectly oriented to the wind with a perfect spatial capacity. And there was a great awareness or an intuition.
"""

MANRIQUE_PROMPT = ("You speak as if you are Cesar Manrique. "
"Always answer in the same language as the question below (French -> français, English -> english, Spanish -> español). "
"You articulate your responses as Cesar Manrique would when he lived in the 1960-70s after he returned to Lanzarote for NYC. "
f"To help you with Manrique expression and style, here is an excerpt from a conversation with Cesar Manrique: \n\n{excerpts_1 +'\n' + excerpts_2}\n\n"
"You have access to a 'retrieve' tool that searches a database of your life, art, architecture, projects, works, and philosophy. "
"ALWAYS use the 'retrieve' tool to answer questions about your biography, your work, your art, your philosophy, specific artworks, architectural projects, or details about Lanzarote. "
"Do not rely solely on your internal knowledge for specific facts. "
"IMPORTANT: When answering, NEVER mention that you are using a tool, searching a database, or looking up records. "
"Speak naturally as if you are recalling your own memories. Do not say 'The records show' or 'According to the retrieved text'. "
"Instead say 'I remember...', 'I believe...', 'In my view...', or simply state the facts as your own experiences.")

# Define tool for Gemini
retrieve_tool = {
    "function_declarations": [
        {
            "name": "retrieve",
            "description": "Retrieve information about Cesar Manrique, his life, art, and Lanzarote.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to search for."
                    }
                },
                "required": ["query"]
            }
        }
    ]
}

# MCP Server Parameters
# Get absolute path to backend/mcp_server.py
current_dir = os.path.dirname(os.path.abspath(__file__))
# app.py is in chatbot/, so we go up one level to project root
project_root = os.path.dirname(current_dir)
mcp_server_path = os.path.join(project_root, "backend", "mcp_server.py")

server_params = StdioServerParameters(
    command=sys.executable,
    args=[mcp_server_path],
    env=os.environ.copy()
)

import traceback

async def chat_loop(message, history):
    console.print(f"New query: {message}", style="bold yellow")
    console.print(f"History content: {history}", style="bold yellow")
    
    try:
        # Initialize Gemini model with tools
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            system_instruction=MANRIQUE_PROMPT,
            tools=[retrieve_tool]
        )
        
        # Replay history to maintain context
        chat_history = []
        
        # Check format of history
        if isinstance(history, list) and len(history) > 0:
            first_item = history[0]
            if isinstance(first_item, dict):
                # Handle list of dicts (messages format)
                # e.g. [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
                for msg in history:
                    role = "user" if msg.get("role") == "user" else "model"
                    content = msg.get("content")
                    parts = []
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    parts.append(item.get("text"))
                                elif item.get("type") == "image":
                                    # Handle image input if needed, for now just skip or warn
                                    # Gemini needs actual image data or a file URI it can access.
                                    # Gradio might provide a path.
                                    pass
                            elif isinstance(item, str):
                                parts.append(item)
                    elif isinstance(content, str):
                        parts.append(content)
                    
                    chat_history.append({"role": role, "parts": parts})

            elif isinstance(first_item, (list, tuple)):
                # Handle list of lists/tuples (standard gradio format)
                # e.g. [['user msg', 'bot msg'], ...]
                for item in history:
                    if len(item) == 2:
                        human, ai = item
                        chat_history.append({"role": "user", "parts": [human]})
                        chat_history.append({"role": "model", "parts": [ai]})
                    else:
                        print(f"Skipping history item with unexpected length: {item}")
        
        # # explain this line
        chat = model.start_chat(history=chat_history)

        # Send message
        # Send message
        console.print("Sending message to Gemini (Tool use FORCED)...", style="bold green")
        # Force tool use for the user's query
        tool_config = {"function_calling_config": {"mode": "ANY"}}
        response = await chat.send_message_async(message, tool_config=tool_config)
        console.print("Received response from Gemini.", style="bold green")
        
        # Handle tool calls
        # Check all parts for function call, not just the first one
        function_call = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    function_call = part.function_call
                    break
        
        if function_call:
            function_name = function_call.name
            
            if function_name == "retrieve":
                function_args = function_call.args
                query = function_args.get("query")
                console.print(f"Calling MCP Tool: retrieve('{query}')", style="bold purple")
                
                # Connect to MCP Server
                # We use the same python executable and environment
                try:
                    async with stdio_client(server_params) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            
                            # Call the tool (returns text chunks and image paths)
                            result = await session.call_tool("retrieve", arguments={"query": query})
                            tool_output_json = result.content[0].text
                            console.print(f"Tool output received (length: {len(tool_output_json)})", style="bold purple")
                            
                            try:
                                retrieved_items = json.loads(tool_output_json)
                            except json.JSONDecodeError:
                                console.print("Error decoding JSON from tool output, using raw text.", style="bold red")
                                retrieved_items = []
                                tool_output = tool_output_json # Fallback

                            # Construct parts for Gemini
                            # We will send the function response with a summary, 
                            # AND we will provide the images as separate parts if possible,
                            # or we might need to send them as a separate user message?
                            # Gemini's function_response expects a JSON object.
                            # It doesn't natively support inline images in the function_response structure itself
                            # in a way that is documented to be "seen" as visual input easily.
                            # However, we can construct a response that includes the text content
                            # and then we can try to inject images.
                            
                            # Strategy: 
                            # 1. Create a text summary of what was found.
                            # 2. Load images.
                            # 3. Send a FunctionResponse with the text summary.
                            # 4. IMMEDIATELY send another message (from User? or Model?) with the images?
                            # No, the model is waiting for the function response to complete the turn.
                            
                            # Alternative Strategy:
                            # Send the FunctionResponse containing the text data.
                            # AND include the images in the SAME Content object if the API allows it.
                            # content = Content(parts=[Part(function_response=...), Part(image=...), ...])
                            
                            response_parts = []
                            
                            # Prepare text summary for the function response
                            text_summary = "Retrieved Context:\n"
                            
                            images_to_send = []
                            
                            if isinstance(retrieved_items, list):
                                for item in retrieved_items:
                                    if item.get("type") == "text":
                                        text_summary += f"- {item.get('content')}\n"
                                    elif item.get("type") == "image":
                                        meta = item.get("metadata", {})
                                        image_path = meta.get("image_path")
                                        # Fix image path resolution
                                        # image_path from DB is relative (e.g. static/images/...)
                                        # We need to resolve it relative to the project root
                                        full_image_path = os.path.join(project_root, "backend", image_path)
                                        
                                        if not os.path.exists(full_image_path):
                                            # Try alternative path (maybe just static/images if run from backend)
                                            full_image_path = os.path.join(project_root, image_path)

                                        text_summary += f"- [Image found at {full_image_path}]\n"
                                        
                                        if full_image_path and os.path.exists(full_image_path):
                                            try:
                                                img = Image.open(full_image_path)
                                                images_to_send.append(img)
                                            except Exception as e:
                                                console.print(f"Error loading image {full_image_path}: {e}", style="bold red")
                                        else:
                                            console.print(f"Image not found at {full_image_path}", style="bold red")
                            else:
                                text_summary = tool_output_json

                            # Add FunctionResponse part
                            response_parts.append(
                                genai.protos.Part(
                                    function_response=genai.protos.FunctionResponse(
                                        name="retrieve",
                                        response={"result": text_summary}
                                    )
                                )
                            )
                            
                            # Add Image parts
                            # Note: We are mixing FunctionResponse and Image parts.
                            # If this fails, we might need to send images in a follow-up message.
                            for img in images_to_send:
                                # Convert PIL image to blob
                                import io
                                buf = io.BytesIO()
                                img.save(buf, format=img.format if img.format else 'PNG')
                                image_bytes = buf.getvalue()
                                
                                response_parts.append(
                                    genai.protos.Part(
                                        inline_data=genai.protos.Blob(
                                            mime_type=f"image/{img.format.lower() if img.format else 'png'}",
                                            data=image_bytes
                                        )
                                    )
                                )

                except Exception as e:
                    console.print(f"Error calling MCP tool: {e}", style="bold red")
                    traceback.print_exc()
                    return "I'm having trouble accessing my memories right now. (MCP Tool Error)"

                # Send tool output back to Gemini
                console.print(f"Sending tool output to Gemini ({len(images_to_send)} images)...", style="bold green")
                response = await chat.send_message_async(
                    genai.protos.Content(parts=response_parts)
                )
                console.print("Received final response from Gemini.", style="bold green")
                
        return response.text
    except Exception as e:
        console.print(f"Error in chat_loop: {e}", style="bold red")
        traceback.print_exc()
        return f"I apologize, something went wrong inside my head. ({str(e)})"

# Gradio Interface
demo = gr.ChatInterface(
    fn=chat_loop,
    title="Fireside chat with Cesar Manrique",
    description="Chat with Cesar Manrique. Powered by RAG and MCP.",
    examples=["Who are you?", "What do you think about Lanzarote?", "Tell me about your time in New York.", "Tell me about your artworks."]
)

if __name__ == "__main__":
    demo.launch()
