# Chatbot Backend

This project contains the backend for a chatbot application. It's built with FastAPI and uses Poetry for dependency management.

## Prerequisites

- Python 3.7+
- pip (Python package installer)

## Setup

1. Install Poetry (if not already installed):

   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

   For Windows, you can use:

   ```powershell
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   ```

2. Clone the repository:

   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

3. Install dependencies:

   ```bash
   poetry install
   ```

4. Set up environment variables:
Create a .env file in the root directory with the following content:

```
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=chatbot_db
```
Adjust these values according to your MongoDB setup if necessary.

## Running the Application

1. Activate the Poetry shell:

   ```bash
   poetry shell
   ```

2. Start the FastAPI server using uvicorn:

   ```bash
   uvicorn chatbot_backend.main:app --reload
   ```

   The `--reload` flag enables hot reloading, which is useful during development.

3. The server should now be running at `http://localhost:8000`

## API Documentation

Once the server is running, you can access the automatic interactive API documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`


## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
