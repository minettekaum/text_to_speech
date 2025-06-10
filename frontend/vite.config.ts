import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	preview: {
		host: true,
		port: 4173,
		strictPort: true,
		allowedHosts: ['soft-lexine-challenge-d3e578f4.koyeb.app']
	}
});
