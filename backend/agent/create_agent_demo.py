
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.tools import tool


# 1. Define a tool

@tool
def lookup_kanji(character: str) -> str:
    """Look up information about a Japanese kanji character."""

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


# 2. Initialize the model

model = ChatOllama(
    model="qwen2.5:7b",
    temperature=0,
)


# 3. Create the agent

agent = create_agent(
    model=model,
    tools=[lookup_kanji],
    system_prompt=(
        "You are a Japanese kanji learning assistant. "
        "Use the lookup_kanji tool when answering questions "
        "about kanji. Explain the results clearly."
    ),
)


# 4. Invoke the agent

result = agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": "Tell me about the kanji 学."
        }
    ]
})



# 5. Display the conversation

print("\n========== AGENT EXECUTION ==========\n")

for message in result["messages"]:

    print(f"\n{message.type.upper()}:")

    # Not every message has tool_calls
    tool_calls = getattr(message, "tool_calls", [])

    if tool_calls:
        print("Tool calls:", tool_calls)
    else:
        print(message.content)

