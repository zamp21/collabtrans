default_params = {
    "thinking": "default",
    "chunk_size": 3000,
    "concurrent": 30,
    "temperature": 0.7,
    "timeout": 120,  # Default 120 seconds (2 minutes) - reasonable for most translation tasks
    # Note: Actual timeout is capped at 60s for Ollama and 120s for cloud APIs in Agent class
    "retry": 2  # Increased retry count for better reliability
}
