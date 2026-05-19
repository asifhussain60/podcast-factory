Refined Execution Prompt
BLUF

Create a standardized, self-contained HTML view system for the podcast agent workspace. Add a new visual capabilities view, convert the existing acceptance criteria document into an HTML view, redesign index.html, introduce a reusable CSS theme, and define a dedicated repeatable agent for generating future views without creating file sprawl.

Objective

Build and organize a polished set of non-technical HTML views under:

/Users/ahmac/Code/Journal/_workspace/plan/view/

The views should explain podcast agent capabilities clearly using modern, visual, self-contained HTML pages with rich diagrams, consistent styling, and reusable structure.

Required Files and Locations

Create or update only the following areas to avoid sprawl:

/Users/ahmac/Code/Journal/_workspace/plan/view/

Suggested structure:

view/
├── index.html
├── podcast-capabilities.html
├── acceptance-criteria.html
├── assets/
│   ├── css/
│   │   └── theme.css
│   └── js/
│       └── view-common.js
└── agents/
    └── view-generation-agent.md

Do not create unrelated folders or duplicate assets elsewhere.

Tasks
1. Create podcast-capabilities.html

Create:

/Users/ahmac/Code/Journal/_workspace/plan/view/podcast-capabilities.html

This page should depict and explain, for non-technical users, the capabilities the podcast agent will possess.

The page must be self-contained from a navigation perspective and must not navigate away from itself. Internal tabs, accordions, modals, expandable cards, and anchored sections are allowed.

The view should include rich explanatory visuals using SVG and D3.js-style diagrams, including:

Capability mind map
End-to-end flowchart
Data flow diagram
Agent lifecycle diagram
Content pipeline chart
Human-in-the-loop review flow
Risk and quality control matrix
Capability maturity or roadmap chart

The content should explain capabilities such as:

Topic discovery
Guest and source research
Episode planning
Script and outline generation
Audio asset coordination
Transcript handling
Show note generation
Publishing support
Social media repurposing
Analytics review
Feedback incorporation
Quality checks
Brand consistency
Human approval checkpoints

Use language suitable for non-technical stakeholders.

2. Convert acceptance criteria.md to HTML

Find the current acceptance criteria markdown file and convert it into:

/Users/ahmac/Code/Journal/_workspace/plan/view/acceptance-criteria.html

Requirements:

Preserve the original meaning and structure.
Improve readability for browser viewing.
Apply the shared theme.
Use cards, accordions, checklists, and status sections where appropriate.
Do not delete the original markdown unless explicitly required by the existing project convention.
3. Delete and redesign index.html

Delete the current index.html content and redesign it using the same visual framework and theme.

The new index.html should serve as a landing page for the workspace views.

It should include:

Clear title and purpose
Navigation cards linking to available views
Brief descriptions of each view
Consistent visual design using the shared theme
No external page navigation beyond local workspace views
Responsive layout
Status or progress summary section
Clear callouts for non-technical users

Include links to:

podcast-capabilities.html
acceptance-criteria.html

Use relative paths only.

4. Create a shared CSS theme

Create:

/Users/ahmac/Code/Journal/_workspace/plan/view/assets/css/theme.css

The theme should standardize all views.

Include reusable styles for:

Layout shell
Header
Navigation cards
Section cards
Tabs
Accordions
Diagram containers
Callouts
Badges
Buttons
Tables
Checklists
Responsive grids
Print-friendly behavior

Use a modern visual style inspired by Tailwind and Material Design.

Because the views must work over the file:// protocol, avoid relying on build tools or remote-only dependencies. Prefer plain CSS and self-contained browser-compatible JavaScript.

5. Use browser-safe libraries

The views must work when opened directly with:

file:///Users/ahmac/Code/Journal/_workspace/plan/view/index.html

Use libraries only if they can load reliably under the file:// protocol.

Acceptable approaches:

Inline SVG
Local plain JavaScript
Local or CDN D3.js only if graceful fallback exists
No bundlers
No server dependency
No framework build step
No package manager requirement

If D3.js is unavailable, diagrams should still render using inline SVG or native HTML/CSS.

6. Create a dedicated repeatable view-generation agent

Create:

/Users/ahmac/Code/Journal/_workspace/plan/view/agents/view-generation-agent.md

This agent should define a reusable process for generating future views.

It should include:

Purpose
Scope
Inputs required
Output folder rules
Naming conventions
Theme requirements
Diagram requirements
Accessibility requirements
File containment rules
Acceptance criteria
Repeatable execution checklist

The agent should be written so it can be reused whenever a new visual planning view is needed.

Design Requirements

All views must follow the shared theme and use consistent:

Typography
Colors
Spacing
Card design
Diagram styling
Navigation behavior
Accessibility patterns
Responsive behavior

The visual style should feel:

Executive-ready
Clear for non-technical users
Modern
Spacious
Informative
Consistent across all pages
Interaction Requirements

Use tabs and accordions where helpful to maximize screen real estate.

Allowed:

Tabs
Accordions
Expandable cards
Hover states
Internal anchors
Diagram toggles
Collapsible explanations

Not allowed:

Navigating away from the view for core content
Requiring a local server
Requiring a build process
Creating scattered files outside the approved folder structure
Accessibility Requirements

Each HTML view must include:

Semantic HTML
Proper heading hierarchy
Descriptive section titles
Keyboard-accessible controls
Sufficient color contrast
Alt text or text equivalents for diagrams
Print-friendly layout
Responsive design for desktop and tablet screens
Acceptance Criteria
Sunny-Day Path

The implementation is successful when:

podcast-capabilities.html exists under view/.
acceptance-criteria.html exists under view/.
index.html has been fully redesigned.
assets/css/theme.css exists and is used by all HTML views.
agents/view-generation-agent.md exists.
All views open correctly using the file:// protocol.
All navigation uses relative local paths.
The podcast capabilities view includes multiple rich SVG or D3-style diagrams.
The views are understandable to non-technical users.
The folder structure remains contained and organized.
Rainy-Day Path

The implementation should still be acceptable if:

D3.js cannot load, as long as diagrams gracefully fallback to inline SVG or native HTML/CSS.
The original markdown acceptance criteria file remains in place, provided the HTML version is created.
External libraries are unavailable, provided the HTML pages still render cleanly and remain functional.

The implementation is not acceptable if:

Any view requires a local server.
Any view requires a build step.
Files are scattered outside the approved workspace.
The pages rely on broken external dependencies.
The diagrams are purely decorative and do not explain the podcast agent flow.
The index page is not redesigned.
The theme is not shared across views.
Output Format

After completing the work, provide a concise implementation summary with:

## Completed

- Created/updated files
- Key design decisions
- How to open the views
- Any assumptions made
- Any known limitations

Do not include unnecessary explanation or unrelated files.