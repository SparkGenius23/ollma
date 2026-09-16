import ollama

# Define the message you want to send to the model
messages = [
    {
        'role': 'user',
        'content': 'Explain the concept of black holes in simple terms.',
    },
]

# Send the chat request to the gpt-oss:20b model
response = ollama.chat(model='gpt-oss:20b', messages=messages)

# Print the model's response content
print(response['message']['content'])

# You can also stream the response
# stream = ollama.chat(
#     model='gpt-oss:20b',
#     messages=messages,
#     stream=True,
# )
# for chunk in stream:
#     print(chunk['message']['content'], end='', flush=True)

