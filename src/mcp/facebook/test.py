import asyncio
from mcp.facebook.analytics import get_pages_field
from mcp.facebook.client import init_client, close_client, GraphAPIError

ACCESS_TOKEN = "EAARSt8dYWZCYBRYkZAZArgZC8jZCkZCaUqaYjiq9qE5F8N6DPwAdoZCXZBMAc2Oa5UJZAEe3Cgo1xNRJuP6ZBOigUGuh1VN62QPdY3gTgFJIssZCLjY8gVwaCsrxToR4tWqZBZBmQe4pZAInK2rzmHfTP5nE9aY6xGp7Y2kLuLSh8ZAIo2m6EEaZC0HHyvRSsolVyZAm9KvDqXKicxra1HlVmf9v0KmyIKMx17OqQKpXo"

async def main():
    # Initialize once — simulates MCP server startup
    init_client(ACCESS_TOKEN)
    try:
        fb_pages = await get_pages_field("name")
        print(f"Pages: {fb_pages}")
        # for page in fb_pages:
        #     print(f"[{page.id}] {page.name}  |  fans: {page.fan_count}  |  category: {page.category}")
    except GraphAPIError as e:
        print(f"Graph API error (code {e.code}, subcode {e.subcode}): {e}")
    finally:
        await close_client()

asyncio.run(main())