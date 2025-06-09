# Use Node.js as base image
FROM node:20-slim

# Install pnpm
RUN npm install -g pnpm

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PORT=5173
ENV HOST=0.0.0.0
ENV NODE_ENV=production

# Build the application with environment variables
ARG VITE_BACKEND_URL
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL

RUN pnpm build

EXPOSE 5173

# Command to run the application using pnpm preview
CMD ["pnpm", "preview", "--host", "0.0.0.0"]