# podsum

Podcast Summariser

## Backend Setup

The backend is a FastAPI application managed with [uv](https://github.com/astral-sh/uv), a fast Python package manager.

### Prerequisites

-   Python 3.10 or higher
-   [uv](https://github.com/astral-sh/uv) - Install with:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

### Installation

1. Navigate to the backend directory:

    ```bash
    cd backend
    ```

2. Create a virtual environment (if not already created):

    ```bash
    uv venv
    ```

3. Install dependencies:
    ```bash
    uv pip install -r requirements.txt
    ```

### Running the Application

From the `backend` directory, start the development server with auto-reload:

```bash
cd backend
uv run main.py
```

The server will start at `http://localhost:8000`

### API Endpoints

-   **Health Check**: `GET /health` - Returns `{"status": "ok"}`
-   **Generate Summary**: `POST /api/generate` - Accepts `{"input": "string"}` and returns podcast summary data
-   **API Documentation**: `http://localhost:8000/docs` - Interactive Swagger UI
-   **Alternative Docs**: `http://localhost:8000/redoc` - ReDoc documentation

### Development

The application uses:

-   **FastAPI** for the web framework
-   **Uvicorn** as the ASGI server
-   **Pydantic** for data validation
-   **uv** for dependency management

The `main.py` file contains the FastAPI app and can be run directly. Auto-reload is enabled in development mode, so changes to the code will automatically restart the server.
