"""
Serve the Textual app as a web application
Run with: python serve_app.py
"""
from textual_serve.server import Server

if __name__ == "__main__":
    # Serve the Textual app on http://localhost:8000 (localhost only)
    server = Server(
        "python textual_app.py",
        host="localhost",  # Localhost only - not accessible from other machines
        port=8000,
        debug=True,
    )

    print("🌐 Starting Agent Tool Manager web server...")
    print("📍 Access at: http://localhost:8000")
    print("Press Ctrl+C to stop")

    server.serve()
