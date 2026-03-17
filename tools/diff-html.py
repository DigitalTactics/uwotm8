#!/usr/bin/env python3
"""Generate an HTML side-by-side diff of two files and optionally serve it.

Usage:
    python tools/diff-html.py before.txt after.txt              # creates diff.html
    python tools/diff-html.py before.txt after.txt -o out.html  # custom output path
    python tools/diff-html.py before.txt after.txt --serve      # creates diff.html and serves on port 8080
    python tools/diff-html.py before.txt after.txt --serve 9090 # custom port
"""

import argparse
import difflib
import http.server
import socket
import sys
from pathlib import Path


def get_local_ip() -> str:
    """Get the machine's local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def generate_diff_html(
    before_path: str,
    after_path: str,
    output_path: str = "diff.html",
    before_label: str | None = None,
    after_label: str | None = None,
) -> str:
    """Generate an HTML side-by-side diff file.

    Args:
        before_path: Path to the original file.
        after_path: Path to the modified file.
        output_path: Where to write the HTML output.
        before_label: Label for the left column.
        after_label: Label for the right column.

    Returns:
        The output file path.
    """
    with open(before_path) as f:
        before = f.readlines()
    with open(after_path) as f:
        after = f.readlines()

    before_label = before_label or f"BEFORE ({Path(before_path).name})"
    after_label = after_label or f"AFTER ({Path(after_path).name})"

    d = difflib.HtmlDiff(wrapcolumn=80)
    result = d.make_file(before, after, fromdesc=before_label, todesc=after_label, context=False)

    result = result.replace(
        "</head>",
        """
<style>
    body { font-family: system-ui, -apple-system, sans-serif; margin: 20px; }
    table.diff { font-size: 14px; border-collapse: collapse; width: 100%; }
    td { padding: 4px 8px; vertical-align: top; }
    .diff_header { background-color: #e8e8e8; font-weight: bold; }
    .diff_next { background-color: #c8c8c8; }
    .diff_add { background-color: #aaffaa; }
    .diff_chg { background-color: #ffff77; }
    .diff_sub { background-color: #ffaaaa; }
    td.diff_header { text-align: center; }
    span.diff_add { background-color: #aaffaa; }
    span.diff_chg { background-color: #ffff77; }
    span.diff_sub { background-color: #ffaaaa; }
</style>
</head>""",
    )

    with open(output_path, "w") as f:
        f.write(result)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an HTML side-by-side diff of two files.")
    parser.add_argument("before", help="Path to the original file")
    parser.add_argument("after", help="Path to the modified file")
    parser.add_argument("-o", "--output", default="diff.html", help="Output HTML file path (default: diff.html)")
    parser.add_argument("--before-label", help="Label for the left column")
    parser.add_argument("--after-label", help="Label for the right column")
    parser.add_argument(
        "--serve",
        nargs="?",
        const=8080,
        type=int,
        metavar="PORT",
        help="Serve the diff on a local HTTP server (default port: 8080)",
    )

    args = parser.parse_args()

    output = generate_diff_html(
        args.before,
        args.after,
        output_path=args.output,
        before_label=args.before_label,
        after_label=args.after_label,
    )

    print(f"Diff written to: {output}")

    if args.serve is not None:
        ip = get_local_ip()
        port = args.serve
        print(f"Serving at: http://{ip}:{port}/{output}")
        print("Press Ctrl+C to stop.")

        handler = http.server.SimpleHTTPRequestHandler
        server = http.server.HTTPServer(("0.0.0.0", port), handler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            server.server_close()


if __name__ == "__main__":
    main()
