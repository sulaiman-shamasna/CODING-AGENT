"""Playwright MCP Server - provides browser automation via MCP protocol."""

import os
import json
import asyncio
from typing import Any, Dict, List, Optional


class PlaywrightServer:
    """MCP server for Playwright browser automation."""

    def __init__(self):
        """Initialize Playwright server."""
        self.browser = None
        self.page = None
        self.tools = {
            "navigate": self.navigate,
            "screenshot": self.screenshot,
            "click": self.click,
            "type": self.type_text,
            "get_text": self.get_text,
            "get_html": self.get_html,
        }

    async def initialize(self):
        """Initialize Playwright browser."""
        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch()
            self.page = await self.browser.new_page()
        except ImportError:
            print("Warning: Playwright not installed. Install with: pip install playwright")
            print("Then run: playwright install")

    async def navigate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate to URL."""
        try:
            url = params.get("url")
            if not url:
                return {"error": "url parameter required"}

            if not self.page:
                await self.initialize()

            await self.page.goto(url)
            return {"success": True, "url": url}

        except Exception as e:
            return {"error": str(e)}

    async def screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Take screenshot."""
        try:
            path = params.get("path")
            if not path:
                return {"error": "path parameter required"}

            if not self.page:
                return {"error": "No page loaded. Navigate first."}

            await self.page.screenshot(path=path)
            return {"success": True, "path": path}

        except Exception as e:
            return {"error": str(e)}

    async def click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Click element."""
        try:
            selector = params.get("selector")
            if not selector:
                return {"error": "selector parameter required"}

            if not self.page:
                return {"error": "No page loaded. Navigate first."}

            await self.page.click(selector)
            return {"success": True, "selector": selector}

        except Exception as e:
            return {"error": str(e)}

    async def type_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Type text into element."""
        try:
            selector = params.get("selector")
            text = params.get("text")

            if not selector:
                return {"error": "selector parameter required"}
            if not text:
                return {"error": "text parameter required"}

            if not self.page:
                return {"error": "No page loaded. Navigate first."}

            await self.page.fill(selector, text)
            return {"success": True, "selector": selector}

        except Exception as e:
            return {"error": str(e)}

    async def get_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get text from element."""
        try:
            selector = params.get("selector")
            if not selector:
                return {"error": "selector parameter required"}

            if not self.page:
                return {"error": "No page loaded. Navigate first."}

            text = await self.page.text_content(selector)
            return {"text": text, "selector": selector}

        except Exception as e:
            return {"error": str(e)}

    async def get_html(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get HTML from page or element."""
        try:
            if not self.page:
                return {"error": "No page loaded. Navigate first."}

            selector = params.get("selector")
            if selector:
                html = await self.page.inner_html(selector)
            else:
                html = await self.page.content()

            return {"html": html}

        except Exception as e:
            return {"error": str(e)}

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request."""
        tool_name = request.get("tool")
        params = request.get("params", {})

        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}

        tool_func = self.tools[tool_name]
        return await tool_func(params)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get tool schemas for MCP discovery."""
        return [
            {
                "name": "navigate",
                "description": "Navigate to URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to navigate to"}
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "screenshot",
                "description": "Take screenshot",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to save screenshot",
                        }
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "click",
                "description": "Click element",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector",
                        }
                    },
                    "required": ["selector"],
                },
            },
            {
                "name": "type",
                "description": "Type text into element",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector",
                        },
                        "text": {"type": "string", "description": "Text to type"},
                    },
                    "required": ["selector", "text"],
                },
            },
            {
                "name": "get_text",
                "description": "Get text from element",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector",
                        }
                    },
                    "required": ["selector"],
                },
            },
            {
                "name": "get_html",
                "description": "Get HTML from page or element",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector (optional)",
                        }
                    },
                },
            },
        ]

    async def cleanup(self):
        """Clean up resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


async def main():
    """Main entry point for stdio MCP server."""
    import sys

    server = PlaywrightServer()

    # Simple stdio protocol
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)

            if request.get("method") == "tools/list":
                response = {"tools": server.get_tool_schemas()}
            else:
                response = await server.handle_request(request)

            print(json.dumps(response), flush=True)

        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)

    await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

