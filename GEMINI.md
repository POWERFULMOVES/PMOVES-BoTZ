# GEMINI Agent Instructions for PMOVES-BoTZ Refactoring

## 1. Objective

Your primary objective is to refactor the `PMOVES-Kilobots` repository into a single, unified application named `PMOVES-BoTZ`, following the plan outlined in `PMOVES_Edition.md`.

## 2. Core Principles

*   **Single Source of Truth:** Eliminate all redundancies. There should be one canonical location for each piece of configuration, code, or documentation.
*   **Modularity:** The final structure should be modular, with features clearly separated and managed under the `features/` directory.
*   **Consistency:** Ensure that naming conventions, directory structures, and configurations are consistent throughout the repository.

## 3. Refactoring Workflow

Execute the following steps in order. Do not proceed to the next step until the current one is complete and validated.

### Step 1: Consolidate Docker Compose Files

1.  **Analyze Services:** Read all `docker-compose.*.yml` files from the `pmoves_*_pack` directories to identify all unique services and their configurations.
2.  **Create Base Compose File:** Create a new `core/docker-compose/base.yml`. Add all identified services to this file. Use environment variables for all configurable values (ports, API keys, etc.).
3.  **Create Overlays:** Create `core/docker-compose/overlays/development.yml` and `core/docker-compose/overlays/production.yml`.
    *   `development.yml`: Should map ports to the host for easy access during development.
    *   `production.yml`: Should not map ports to the host unless absolutely necessary. It should be optimized for a production deployment.
4.  **Delete Old Compose Files:** Once the new `base.yml` and overlays are created and validated, delete all `docker-compose.*.yml` files from the `pmoves_*_pack` directories.

### Step 2: Unify MCP Configuration

1.  **Merge Catalogs:** Read all `mcp_catalog_*.yaml` and `mcp_mini_portable.yaml` files. Create a new `core/mcp/catalog.yml` and add all unique server definitions to it. Ensure the service names and ports match the new `base.yml`.
2.  **Merge Modes:** Identify all MCP mode files (`*.json`) in the repository. Copy all unique modes to `core/mcp/modes/`. If there are duplicates, analyze them and merge them into a single, definitive version.

### Step 3: Reorganize Feature Directories (Completed)

1.  **Feature Directories:** Feature directories now exist under `features/` (cipher, e2b, metrics, postman, slack, discord, vl_sentinel, n8n, mini, crush, etc.).
2.  **Feature Code Moved:** Code, configurations, and other files related to each feature have been moved from the `pmoves_*_pack` directories into their homes under `features/`.
3.  **Paths Updated:** Paths in the `docker-compose` files, scripts, and related configs have been updated to reference `core/` and `features/` instead of pack directories.
4.  **Staging Folder Archived:** The temporary `Features_folder/` staging directory has been moved under `archive/Features_folder/` after its contents were folded into `features/`. Treat it as read-only history; do not wire new services to it.

### Step 4: Unify Scripts

1.  **Analyze Scripts:** Review all scripts in the repository (`*.sh`, `*.ps1`).
2.  **Create Unified Scripts:** Create a new set of scripts in the `scripts/` directory for:
    *   `start.sh`/`start.ps1`: To start the application using `docker-compose` with the appropriate overlays.
    *   `stop.sh`/`stop.ps1`: To stop the application.
    *   `test.sh`/`test.ps1`: To run all tests.
    *   `setup.sh`/`setup.ps1`: For any initial setup.
3.  **Delete Old Scripts:** Remove the old scripts from the pack directories.

### Step 5: Update Documentation

1.  **Rewrite `README.md`:** Create a new `README.md` that explains the unified `PMOVES-BoTZ` application.
2.  **Update `AGENTS.md`:** Update `AGENTS.md` to reflect the new repository structure and contribution guidelines.
3.  **Delete Old Documentation:** Remove all `README` files and other documentation from the pack directories.

### Step 6: Cleanup

1.  **Remove Pack Directories:** Once all the content from the `pmoves_*_pack` directories has been moved, delete these directories.
2.  **Final Validation:** Run all tests and start the application to ensure that everything is working as expected.

## 4. Safety and Validation

*   **Work Incrementally:** Perform each step of the refactoring as a separate, atomic change.
*   **Test at Each Step:** After each major change (e.g., consolidating compose files), run tests to ensure that you haven't broken anything.
*   **Use the File System Tools:** Use `list_directory`, `read_file`, `write_file`, `replace`, and `run_shell_command` to perform the refactoring.
*   **Be Careful with Deletions:** Do not delete any files until you are sure that their content has been successfully migrated to the new structure.
