# Text-to-Speech Application with Dia-1.6B

- A full-stack text-to-speech application using the Dia-1.6B model, FastAPI backend, and Svelte frontend. 
- Deployment: Pruna and Koyeb
- Demo of the app

![Text-to-Speech App Demo](assets/demo.png)

## Project Structure

The project consists of two main directories:
- `backend/`: Contains the FastAPI server and Dia model implementation.
- `frontend/`: Contains the Svelte frontend application.

## Setup Instructions

- Steps to set up and deploy this project.

## How to Build the Project

- Instructions on how to set up the project from scratch: 
   - **Backend**
   - **Frontend**
   - **Connect backend and frontend**
   - **Deploy on Koyeb**

## Trouble Shooting
- Common troubleshooting steps and solutions.

# (Minette) Next Steps before deployment

- **Deploy on Koyeb**

For the code:
   - **Improve the frontend layout**:
      - Create a chat layout or similar design to clearly distinguish different persons talking.
      - And make it more appealing
   - **Add generation parameters**:
      - Currently, there is a bug where the model adds gibberish after it has "read" the text.
   - **Check inference**
   - **Clean the code**