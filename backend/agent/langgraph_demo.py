
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition


# --------------------------------------------------
# 1. Define a tool
# --------------------------------------------------

@tool
def lookup_kanji(character: str) -> str:
    """Look up information about a Japanese kanji."""

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


tools = [lookup_kanji]


# --------------------------------------------------
# 2. Initialize the model
# --------------------------------------------------

model = ChatOllama(
    model="qwen2.5:7b",
    temperature=0,
)

model_with_tools = model.bind_tools(tools)


# --------------------------------------------------
# 3. Define the assistant node
# --------------------------------------------------

def call_model(state: MessagesState):

    response = model_with_tools.invoke(state["messages"])

    return {"messages": [response]}


# --------------------------------------------------
# 4. Build the graph
# --------------------------------------------------

graph_builder = StateGraph(MessagesState)

# Register nodes
graph_builder.add_node("assistant", call_model)
graph_builder.add_node("tools", ToolNode(tools))

# Starting point
graph_builder.add_edge(START, "assistant")

# Decide whether to call a tool or finish
graph_builder.add_conditional_edges(
    "assistant",
    tools_condition,
)

# Return to assistant after tool execution
graph_builder.add_edge("tools", "assistant")


# --------------------------------------------------
# 5. Compile the graph
# --------------------------------------------------

agent = graph_builder.compile()


# --------------------------------------------------
# 6. Run the graph
# --------------------------------------------------

result = agent.invoke({
    "messages": [
        HumanMessage(content="Tell me about the kanji 学.")
    ]
})


# --------------------------------------------------
# 7. Display the results
# --------------------------------------------------

print("\n========== LANGGRAPH EXECUTION ==========\n")

for message in result["messages"]:

    print(f"\n{message.type.upper()}:")

    tool_calls = getattr(message, "tool_calls", [])

    if tool_calls:
        print("Tool calls:", tool_calls)
    else:
        print(message.content)
