import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Function to determine the backend URL for server-side requests
function getBackendUrl(requestUrl: string): string {
    try {
        const url = new URL(requestUrl);
        const hostname = url.hostname;
        
        // If we're on localhost, use the local backend
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://127.0.0.1:8000';
        }
        
        // If we're on a koyeb.app domain, use the same host but with HTTPS
        if (hostname.endsWith('.koyeb.app')) {
            return `https://${hostname}`;
        }
        
        // Fallback to localhost
        return 'http://127.0.0.1:8000';
    } catch {
        // If URL parsing fails, fall back to localhost
        return 'http://127.0.0.1:8000';
    }
}

export const POST: RequestHandler = async ({ request, url }) => {
    try {
        // Get the request body
        const body = await request.json();
        
        // Get the API URL dynamically
        const API_URL = getBackendUrl(url.toString());
        console.log('Server-side backend URL:', API_URL);
        console.log('Full request URL:', `${API_URL}/api/generate`);
        
        // Forward the request to the backend
        const response = await fetch(`${API_URL}/api/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body),
            // Add timeout and better error handling
            signal: AbortSignal.timeout(60000) // 60 second timeout
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            return json(
                { error: errorData?.detail || 'Failed to generate audio' },
                { status: response.status }
            );
        }

        // Get the audio blob from the response
        const blob = await response.blob();
        
        // Return the audio blob with appropriate headers
        return new Response(blob, {
            headers: {
                'Content-Type': 'audio/wav',
                'Content-Length': blob.size.toString()
            }
        });

    } catch (error) {
        console.error('Error in generate endpoint:', error);
        return json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}; 