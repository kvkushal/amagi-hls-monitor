import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
        errorInfo: null
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error, errorInfo: null };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('Uncaught error:', error, errorInfo);
        this.setState({ error, errorInfo });
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-gray-900 text-white p-8 flex flex-col items-center justify-center">
                    <div className="max-w-2xl w-full bg-gray-800 p-6 rounded-lg border border-red-500 shadow-xl">
                        <h1 className="text-2xl font-bold text-red-500 mb-4">Something went wrong</h1>
                        <div className="bg-black p-4 rounded overflow-auto mb-4 border border-gray-700">
                            <code className="text-red-400 font-mono text-sm whitespace-pre-wrap">
                                {this.state.error && this.state.error.toString()}
                            </code>
                        </div>
                        <div className="bg-black p-4 rounded overflow-auto h-64 border border-gray-700">
                            <code className="text-gray-400 font-mono text-xs whitespace-pre-wrap">
                                {this.state.errorInfo && this.state.errorInfo.componentStack}
                            </code>
                        </div>
                        <button
                            className="mt-6 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white font-medium"
                            onClick={() => window.location.reload()}
                        >
                            Reload Page
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
