from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="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"
)
query = input('ask ai : ')
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[
        {"role": "user", "content": query}
    ]
)

print(response.choices[0].message.content)