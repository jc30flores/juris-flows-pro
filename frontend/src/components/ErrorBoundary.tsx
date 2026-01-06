import React from "react";

type Props = { children: React.ReactNode };
type State = { hasError: boolean; message?: string };

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(err: unknown): State {
    const message = err instanceof Error ? err.message : "Unexpected error";
    return { hasError: true, message };
  }

  componentDidCatch(error: unknown, info: unknown) {
    console.error("[ErrorBoundary] Caught error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24 }}>
          <h2 style={{ marginBottom: 8 }}>Algo falló en la interfaz</h2>
          <p style={{ opacity: 0.8, marginBottom: 16 }}>
            {this.state.message ?? "Error inesperado"}
          </p>
          <button onClick={() => window.location.reload()}>Recargar</button>
        </div>
      );
    }
    return this.props.children;
  }
}
