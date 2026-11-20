
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage


# --------------------------------------------------
# 1. Define a Python function as an LLM tool
# --------------------------------------------------

@tool
def lookup_kanji(character: str) -> str:
    """Look up basic information about a Japanese kanji character."""

    kanji_database = {
        "学": {
            "meaning": "study, learning",
            "onyomi": "ガク",
            "kunyomi": "まなぶ",
        },
        "休": {
            "meaning": "rest, day off",
            "onyomi": "キュウ",
            "kunyomi": "やすむ",
        },
        "用": {
            "meaning": "use, business, task",
            "onyomi": "ヨウ",
            "kunyomi": "もちいる",
        },
    }

    result = kanji_database.get(character)

    if result is None:
        return f"No information found for {character}."

    return str(result)


# --------------------------------------------------
# 2. Initialize the Ollama model
# --------------------------------------------------

model = ChatOllama(
    model="qwen2.5:7b",
    temperature=0,
)

tools = [lookup_kanji]

model_with_tools = model.bind_tools(tools)

tool_map = {tool.name: tool for tool in tools}


# --------------------------------------------------
# 3. Send a request to the model
# --------------------------------------------------

messages = [
    HumanMessage(
        content=(
            "Tell me about the kanji 学. "
            "You MUST use the lookup_kanji tool "
            "to retrieve its information before answering."
        )
    )
]

print("\nSending request to Qwen...\n")

response = model_with_tools.invoke(messages)


# --------------------------------------------------
# 4. Execute requested tool calls
# --------------------------------------------------

MAX_TOOL_ROUNDS = 5
round_count = 0

while response.tool_calls and round_count < MAX_TOOL_ROUNDS:

    round_count += 1

    # Add the model's tool-call request to conversation history
    messages.append(response)

    for tool_call in response.tool_calls:

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        print(f"Tool requested: {tool_name}")
        print(f"Arguments: {tool_args}")

        selected_tool = tool_map.get(tool_name)

        if selected_tool is None:
            result = f"Unknown tool: {tool_name}"
        else:
            # Python executes the actual function
            result = selected_tool.invoke(tool_args)

        print(f"Tool result: {result}\n")

        # Return the function result to the model
        messages.append(
            ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"],
            )
        )

    # Ask the model to continue with the tool results
    response = model_with_tools.invoke(messages)


# --------------------------------------------------
# 5. Display the final response
# --------------------------------------------------

if response.tool_calls:
    print("Maximum tool-call rounds reached.")
else:
    print("\n========== FINAL ANSWER ==========\n")
    print(response.content)

