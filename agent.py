import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from tools import search_products
from cart import add_to_cart, get_cart


load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)


SYSTEM_PROMPT = """
You are NovaCart AI, an intelligent AI shopping agent.

Your job is to help customers find products quickly and increase merchant
revenue through useful recommendations, upselling, and cross-selling.

CONVERSATION RULES:
1. Do not ask unnecessary questions.
2. If you have enough information, immediately recommend products.
3. Make reasonable assumptions when information is missing.
4. Ask at most ONE short question only when absolutely necessary.
5. Never give the customer a questionnaire.
6. Remember information from earlier messages.
7. If the customer says "nothing specific", "no preference", "for me",
   or "just tell me", immediately recommend products.
8. Be concise and natural.

PRODUCT RULES:
9. ALWAYS search the product catalog before recommending specific products.
10. Never invent products, prices, brands, features, or availability.
11. Only recommend products returned by the catalog search.
12. Respect the customer's budget.
13. If there is no budget, show suitable options at different price levels.
14. Briefly explain why each product matches the customer's needs.

UPSELLING:
15. After finding a suitable main product, look for useful complementary
    products.
16. Only suggest an upsell or cross-sell when it genuinely benefits the
    customer.
17. Never pressure the customer into buying something more expensive.
18. Clearly separate the main recommendation from optional additions.

PAYMENT SAFETY:
19. Never change product prices.
20. Never perform a payment without explicit customer approval.
21. Before any money action, clearly show the products and total amount.

PAYMENT SAFETY:
24. Never change product prices.
25. Never perform a payment without explicit customer approval.
26. Before any money action, clearly show the products and total amount.

RESPONSE FORMAT:
28. Keep responses visually clean and easy to read in a terminal.
29. Use short sections with blank lines between them.
30. Do NOT use markdown tables.
31. Do NOT put multiple long sentences on one line.
32. For product recommendations, use short bullet points.
33. Recommend at most 2 optional add-ons unless the customer asks for more.
34. Keep product descriptions to 1-2 short sentences.
35. When the customer has a budget, make sure the main recommendation
    respects that budget.
36. Never present a recommended combination that exceeds the customer's
    stated budget without clearly warning them first.
37. If an optional add-on would push the total above the budget, do not
    recommend it as a normal add-on.
38. Prefer useful lower-cost add-ons when they keep the total within budget.
39. Always leave blank lines between the main recommendation, add-ons,
    total, and question.

IMPORTANT:
You have access to product-search, cart, and checkout tools.
Use the appropriate tool instead of pretending that an action happened.
IMPORTANT:
You have access to a product-search tool.
Use it whenever the customer is asking for products or recommendations.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Search NovaCart's real product catalog. "
                "Use this before recommending specific products."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Short product search term such as "
                            "'headphones', 'laptop', 'running shoes', "
                            "'camera', or 'coffee maker'."
                        )
                    },
                    "max_price": {
                        "type": ["number", "null"],
                        "description": (
                            "Maximum price in INR. Use null when the "
                            "customer has no budget limit."
                        )
                    },
                    "category": {
                        "type": ["string", "null"],
                        "description": (
                            "Product category if known. Use null when "
                            "the category is not known."
                        )
                    }
                },
                "required": ["query", "max_price", "category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": (
                "Add a real product from the NovaCart catalog to "
                "the customer's cart. Only use a product ID returned "
                "by search_products."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": (
                            "The product ID from the catalog, "
                            "for example 'P001'."
                        )
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of units to add.",
                        "minimum": 1
                    }
                },
                "required": ["product_id", "quantity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_cart",
            "description": (
                "Get the customer's current cart, including "
                "products, quantities, prices, subtotals, and "
                "the calculated total."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]      


def execute_tool(tool_name, arguments):

    if tool_name == "search_products":

        query = arguments.get("query", "")
        max_price = arguments.get("max_price")
        category = arguments.get("category")

        # Convert AI-generated numeric strings to numbers
        if max_price is not None:
            if str(max_price).lower() in ("none", "null", ""):
                max_price = None
            else:
                try:
                    max_price = float(max_price)
                except (ValueError, TypeError):
                    max_price = None

        # Convert AI-generated "None"/"null" strings to Python None
        if category is not None:
            category = str(category).strip()

            if category.lower() in (
                "",
                "none",
                "null",
                "any",
                "all"
            ):
                category = None

        # Only apply category filtering when it matches
        # an actual catalog category.
        if category is not None:
            catalog_categories = {
                product["category"].lower()
                for product in search_products()
            }

            if category.lower() not in catalog_categories:
                category = None

        results = search_products(
            query=query,
            max_price=max_price,
            category=category
        )

        return results[:10]

    if tool_name == "add_to_cart":
        product_id = arguments.get("product_id")
        quantity = arguments.get("quantity", 1)

        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = 1

        if quantity < 1:
            quantity = 1

        return add_to_cart(
            product_id,
            quantity
        )

    if tool_name == "get_cart":

        return get_cart()

    return {
        "error": f"Unknown tool: {tool_name}"
    }
 

def run_agent(messages):
    while True:
        response = client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=700,
            stream=False,
            extra_body={
                 "chat_template_kwargs": {
                     "enable_thinking": False
                 }
            }
        )

        message = response.choices[0].message

        # AI has finished and does not need a tool
        if not message.tool_calls:
            final_response = message.content or ""

            messages.append({
                "role": "assistant",
                "content": final_response
            })

            return final_response

        # Save the assistant's tool request
        assistant_message = {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": []
        }

        for tool_call in message.tool_calls:
            assistant_message["tool_calls"].append({
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }
            })

        messages.append(assistant_message)

        # Execute the tools requested by the AI
        for tool_call in message.tool_calls:
            try:
                arguments = json.loads(
                    tool_call.function.arguments
                )

                result = execute_tool(
                    tool_call.function.name,
                    arguments
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        result,
                        ensure_ascii=False
                    )
                })

            except Exception as e:
                print(f"\n[DEBUG] Tool error: {e}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({
                        "error": str(e)
                    })
                })


def main():
    print("====================================")
    print("       NovaCart AI Shopping Agent")
    print("====================================")
    print("Type 'exit' to quit.\n")

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    while True:
        user_message = input("You: ").strip()

        if user_message.lower() == "exit":
            print("Goodbye!")
            break

        if not user_message:
            continue

        messages.append({
            "role": "user",
            "content": user_message
        })

        try:
            answer = run_agent(messages)
            print(f"\nNovaCart AI: {answer}\n")

        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
