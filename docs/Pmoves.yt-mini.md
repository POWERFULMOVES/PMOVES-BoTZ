

 **powerful custom automation tool**! You are essentially looking to create an **AI Agent** that lives in your terminal and uses its combined knowledge of the Gemini API and the YouTube Data API to manage your playlists.

You would need to build this custom **Gemini CLI Agent** yourself, as there is no pre-built Google tool that combines both account access (YouTube API) and conversational intelligence (Gemini) specifically for playlist management.

Here's the plan for creating a custom Gemini CLI Agent :
PMOVES.YT Mini Agent - Design Notes

Goal
- Define a lightweight PMOVES-BoTZ-compatible **YT mini** agent – one of the CLI mini agents on the PMOVES-BoTZ team – focused on YouTube/media workflows, with a local-first, Ollama-friendly footprint.

Relationship to PMOVES-BoTZ
- PMOVES.YT is part of the layered PMOVES-BoTZ architecture:
  - **CLI mini agent layer**: A local `yt-mini` CLI that can:
    - Bootstrap the YT service it is responsible for (e.g., prepare a local media index, run a one-shot analysis job).
    - Be invoked directly by users or by orchestration agents (gateway / MCP modes).
  - **Service/overlay layer** in this repo:
    - A small Dockerized service wired as an optional `features/yt` overlay, sitting alongside `features/cipher`, `features/docling`, etc.
  - **Gateway / big-bro agents**:
    - MCP modes in `core/mcp/modes/` can call into the YT mini agent via MCP or HTTP to compose workflows (Docling + Cipher + YT, etc.).
- The primary focus is local media indexing and playlist/channel intelligence; cloud APIs (YouTube Data API, etc.) are layered in after the local/Ollama path is healthy.

Local-First Plan (Ollama)
- Embed PMOVES.YT mini as:
  - A local CLI for playlist and channel snapshots (using `yt-dlp` or Invidious where appropriate).
  - An MCP tool or HTTP endpoint for:
    - "Summarize this channel/playlist"
    - "Suggest the next 3 videos given this history"
  - LLM reasoning provided by the same VL/Ollama stack used by PMOVES-BoTZ (no cloud key required).
- Validation hook in this repo (once `features/yt` exists):
  - Add a dedicated smoke test:
    - Verifies the YT mini container/CLI is callable from the BoTZ stack.
    - Ensures basic commands (e.g., dry-run metadata fetch against a test playlist URL) return structured JSON.

Cloud Layering (Later)
- Once local behavior is stable:
  - Add optional bindings for YouTube Data API keys and any recommended media intelligence APIs.
  - Extend smoke tests to:
    - Check API quota usage endpoints.
    - Validate end-to-end flows (playlist fetch → summary via Cipher/Docling → stored memory in Cipher).

Next Steps
- Stand up the `PMOVES.YT` repo with:
  - Minimal CLI skeleton for "yt-mini" workflows (the mini agent itself).
  - A simple docker-compose snippet suitable for a future `features/yt/docker-compose.yml` overlay in PMOVES-BoTZ.
- Wire initial smoke tests here once the first YT mini container/CLI is available, and link them from `docs/SMOKE_TESTS_AND_STAGING.md` and `docs/PMOVES.AI-Edition-Hardened.md` as another team member in the BoTZ mini-agents layer.

---

## 1. Core Components

You need to integrate two main components:

| Component | Purpose | Key Requirement |
| :--- | :--- | :--- |
| **YouTube Data API v3** | To perform actions on your account (read playlist contents, add/remove videos). | **OAuth 2.0 Authorization** to read and write private user data (your playlists). |
| **Gemini API** | To process your natural language requests (e.g., "Move all videos about Python to a new playlist called Python Basics"). | An **API Key** or authenticated access to a Gemini model (like Gemini 2.5 Pro). |
| **Custom CLI Script** | The main application logic, likely written in **Python**, that connects the two APIs. | A library like `google-api-python-client` for YouTube and the Google GenAI SDK for Gemini. |

---

## 2. Gemini Agent Logic

Your CLI script would work like this:

1.  **User Input:** You type a command, like `agent analyze my "AI" playlist`.
2.  **API Call:** The script uses the **YouTube Data API** (`playlistItems.list`) to retrieve the titles, descriptions, and channel names for all videos in your "AI" playlist.
3.  **Gemini Processing:** The script sends this playlist data, along with a structured prompt, to the **Gemini API**. The prompt could be: *"Here is a list of video titles, descriptions, and channels from the user's 'AI' playlist. Analyze them and suggest the top 5 most relevant YouTube channels."*
4.  **Gemini Response:** Gemini returns the list of channels and justification.
5.  **Output & Action:** Your script displays the channels in the terminal. If you then say `agent move all coding videos to new playlist "Coding AI"`, your script uses Gemini to interpret that intent and then executes the necessary `playlistItems.insert` and `playlistItems.delete` calls via the YouTube API.

exopand this to include full access and controll of api for creating a robust implementation 


The open-source **Gemini CLI** project can serve as a great starting point, as it is designed for developers and supports built-in tools and extensions that you could customize for YouTube API calls.

---

## 3. Key API Methods for Your Agent

| Goal | YouTube Data API Method | Description |
| :--- | :--- | :--- |
| **Get All Playlists** | `playlists.list` | Retrieves all your private playlists. |
| **Get Playlist Content** | `playlistItems.list` | Retrieves the video details (title, channel, ID) within a specific playlist. |
| **Create New Playlist** | `playlists.insert` | Creates a new playlist based on Gemini's suggestions. |
| **Add a Video** | `playlistItems.insert` | Adds a video to a specific playlist ID. |
| **Remove a Video** | `playlistItems.delete` | Removes a video from a specific playlist. |

The video "Gemini CLI: Assisting your startup as you scale" gives a high-level overview of what a custom command-line agent can accomplish.

