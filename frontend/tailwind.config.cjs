module.exports = {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'elecard': {
                    'dark': '#2c3e50',
                    'darker': '#1a252f',
                    'blue': '#3b82f6',
                    'gray': '#4a5568',
                    'lightgray': '#718096',
                    'card': '#2c3e50',
                    'border': '#3a4a5a',
                    'bg': '#1a252f',
                },
            },
        },
    },
    plugins: [],
}
