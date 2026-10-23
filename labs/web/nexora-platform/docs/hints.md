# Hints

1. Start by understanding how the application communicates with external resources.
2. Look closely at the API functionality involving URLs.
3. Can you make the server communicate with infrastructure you control?
4. The response does not necessarily need to contain the result of the server-side request.
5. Look for functionality that answers a simple question: Can this URL be reached?
6. What happens if the hostname resolves differently between validation and connection?
7. Consider a deterministic DNS rebinding scenario where validation and the outbound client perform separate lookups.
