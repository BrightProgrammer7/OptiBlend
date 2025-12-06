# Implementation Plan - OptiBlend & Holcim Nexus Integration

## Goal
Merge the OptiBlend landing page with the Holcim Nexus backend and refactor the dashboard to align with the "Industrial AI" visual identity and "Unified Platform" architecture.

## User Review Required
> [!IMPORTANT]
> **Dashboard Integration**: `optimization_lab.html` will be refactored to connect to the `Unified Server` (Port 8000) instead of the standalone `Lab Server` (Port 8082). Ideally, you should run `unified_server.py` to support the new dashboard.

## Proposed Changes

### Frontend - Landing Page (`landing.html`)
- **Visual Overhaul**: Replace the current "Miraj XR / Moroccan Heritage" content with "Holcim Nexus | OptiBlend" branding.
- **Theme**: Apply the "Industrial Sci-Fi" theme (Dark Carbon, Neon Green #5C8C22, Holographic Blue).
- **Sections**:
    - **Hero**: "Industrial AI for Sustainable Cement" with "Launch OptiBlend" CTA.
    - **Features**: Real-time Waste Analysis, Kiln Stability, Green Energy Optimization.
    - **Tech**: Mention "Gemini 2.5 Flash", "Petcoke Substitution", "Vision Systems".
- **Link**: Connect the main CTA to `optimization_lab.html`.

### Frontend - Dashboard (`optimization_lab.html`)
- **Backend Connection**: Update the API call from `http://localhost:8082/solve` to `http://localhost:8000/api/optimize` to use the Unified Platform backend.
- **Refactoring**: 
    - Ensure data payload structure matches `unified_server.py` expectations (it appears compatible).
    - Minor UI tweaks to ensure it perfectly matches the new Landing Page aesthetics (fonts, colors).

## Verification Plan

### Automated Tests
- None (Visual/UI changes).

### Manual Verification
1.  **Launch Server**: Run `python unified_server.py`.
2.  **Open Landing Page**: Open `landing.html` in browser.
    - Verify Design matches "Industrial Sci-Fi".
    - Click "Launch OptiBlend" -> Should open `optimization_lab.html`.
3.  **Test Dashboard**:
    - In `optimization_lab.html`, click "INITIATE SOLVER".
    - Verify it sends a request to `localhost:8000`.
    - Verify results (charts, metrics) appear correctly.
