# Text-to-Speech Application with Dia-1.6B

A full-stack text-to-speech application using the Dia-1.6B model, FastAPI backend, and Svelte frontend.

## Features

- Text-to-speech conversion using the Dia-1.6B model
- Interactive web interface
- Sound effect insertion support
- Real-time audio playback
- Automatic file cleanup

## Prerequisites

- Python 3.10 or higher
- Node.js 16 or higher
- pnpm (for frontend package management)

## Project Structure

The project consists of two main directories:
- `backend/`: Contains the FastAPI server and Dia model implementation
- `frontend/`: Contains the Svelte frontend application

## Setup Instructions

### 1. Clone the Repository

Clone the repository and navigate to the project directory.

### 2. Backend Setup

1. Create and activate a virtual environment
2. Install the required dependencies:
   - fastapi
   - uvicorn
   - soundfile
   - descript-audio-codec
   - safetensors

### 3. Frontend Setup

Navigate to the frontend directory and install dependencies using pnpm.

## Running the Application

1. Start the Backend:
   - Navigate to the backend directory
   - Run the uvicorn server with reload enabled
   - Server will be available at `http://localhost:8000`

2. Start the Frontend:
   - Navigate to the frontend directory
   - Run the development server
   - Access the application at `http://localhost:5173`


## What to add
For the app: 
   - Improve the frontend layout
   - clean the code
Blog post: 
   - More about the model and where to find more about it
   - Step by step on how to build the app
   - How to deploy the model on koyeb

