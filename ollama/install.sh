# Start Ollama server
ollama serve &

# Wait for the server to be ready
while ! echo > /dev/tcp/localhost/11434 2>/dev/null; do
    echo "Waiting for Ollama server to be ready..."
    sleep 2
done

echo "Ollama server is ready. Starting to run model..."

# Run the model
if [ ! -z "${LLM_MODEL}" ]; then
    model=$(echo "$LLM_MODEL" | cut -d'/' -f2)
    echo "Running ${model}..."
    ollama run ${model} /set parameter num_ctx 32768 /set parameter n_ctx_per_seq 32768
fi

# Keep the container running
wait
