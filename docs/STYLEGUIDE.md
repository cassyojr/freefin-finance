# Design System Strategy: The Sovereign Interface



## 1. Overview & Creative North Star

The Creative North Star for this design system is **"The Digital Private Bank."**



Moving away from the cluttered, "SaaS-standard" dashboard, this system treats financial data as high-end editorial content. We reject the rigid, boxy grids of traditional fintech in favor of **Intentional Asymmetry** and **Tonal Depth**. The experience should feel like a custom-tailored suit: precise, authoritative, and sophisticated. We achieve this by prioritizing white space (breathing room) as a functional element, allowing complex data to be "read" rather than just "seen."



---



## 2. Color Theory & Surface Logic

This system moves beyond flat color by utilizing a sophisticated layering of Material-based tokens to create a sense of physical presence.



### The Palette

* **Primary (`#0056d2`):** A commanding "Deep Indigo" used for navigation anchors and primary actions.

* **Secondary (`#00875a`):** "Estate Green." Used exclusively for positive growth, income, and success states to build trust.

* **Tertiary (`#d32f2f`):** "Oxblood Red." A refined, high-contrast red for debt and alerts that feels urgent but not panicked.



### The "No-Line" Rule

**Explicit Instruction:** Designers are prohibited from using 1px solid borders for sectioning or containers. Structural boundaries must be defined solely through background color shifts or subtle tonal transitions.

* *Example:* Place a `surface_container_low` section directly against a `surface` background. The change in hex code is the divider.



### The Glass & Gradient Rule

To prevent the UI from feeling "out-of-the-box," use semi-transparent surface colors with a `backdrop-blur` (Glassmorphism) for floating elements like navigation bars or modal overlays.

* **Signature Texture:** Use a subtle linear gradient (from `primary` to `primary_container`) for main CTAs to add "soul" and professional weight.



---



## 3. Typography: The Editorial Scale

We utilize a dual-typeface system to balance character with extreme legibility.



* **Display & Headlines (Manrope):** A geometric sans-serif with a high x-height. Use `display-lg` (3.5rem) and `headline-md` (1.75rem) to create an authoritative hierarchy. This is the "Voice" of the brand.

* **Data & UI (Inter):** The workhorse. Used for all tables, charts, and body copy. Its neutral tone ensures that complex financial figures remain the focus.

* **Asymmetric Scaling:** Don't be afraid of the "Big Number" trend. Use `display-sm` for account balances to make them the undeniable hero of the page, contrasted against `label-sm` for metadata.



---



## 4. Elevation & Depth (Tonal Layering)

Standard drop shadows are often messy. We achieve depth through a **Layering Principle.**



* **The Stack:**

1. Base: `surface`

2. Section: `surface_container_low`

3. Card/Component: `surface_container_lowest` (This creates a "lifted" effect via brightness rather than shadow).

* **Ambient Shadows:** For floating modals, use a shadow with a blur of `24px` and an opacity of `4%`. The shadow color must be a tinted version of `on_surface` (a deep indigo-grey) rather than pure black.

* **The Ghost Border Fallback:** If a container lacks contrast (e.g., in Dark Mode), use a "Ghost Border": the `outline_variant` token at **15% opacity**.



---



## 5. Components & Primitive Logic



### Buttons (High-Impact)

* **Primary:** `primary` background with `on_primary` text. Use `rounded-sm` (0.125rem) for a subtle roundedness. Use a subtle inner-glow (1px white at 10% opacity on the top edge) for a premium tactile feel.

* **Tertiary:** No background. Use `primary` text. These must rely on the `Spacing Scale (4)` to maintain clickability.



### Cards & Data Lists

* **Forbid Dividers:** Never use a line to separate transactions in a list. Instead, use a vertical spacing of `1.1rem` (`spacing-5`) or alternating tonal shifts between `surface_container` and `surface_container_low`.

* **Contextual Chips:** Use `secondary_container` for income and `tertiary_fixed` for expenses. Chips must have `rounded-full` corners to contrast against the more "architectural" squareness of the dashboard.



### Financial Input Fields

* **State Logic:** On focus, the input should not just change border color, but slightly shift its background to `surface_bright`.

* **The "Money" Input:** For currency entry, use `headline-lg` typography. The currency symbol should be treated as a `label-md` suffix to keep the focus on the value.

* **Height Consistency Rule:** When displaying multiple inputs side-by-side in a flex row, always pin an explicit `line-height` (e.g. `1.4`) and a fixed `height` on the inputs, and set `align-self: start` to override CSS Grid's default `stretch` behaviour inside `<label>` wrappers. Without this, subtle font-metric differences between fields will cause one input to render slightly taller than its sibling.



---



## 6. Do’s and Don’ts



### Do

* **DO** use intentional white space. If a chart feels crowded, increase the padding to `spacing-12` (2.75rem).

* **DO** use `surface_tint` at 5% opacity for large background areas to give the "Dark Mode" a customized, premium warmth.

* **DO** ensure all charts use the `secondary` (success) and `tertiary` (alert) tokens consistently to communicate financial health at a glance.



### Don’t

* **DON'T** use default 1px `#EEEEEE` borders. It breaks the premium "editorial" feel.

* **DON'T** use pure black `#000000` for text. Use `on_surface` (`#1a1c1e`) to keep the typography feeling integrated and soft.

* **DON'T** crowd the screen. If you have 10 data points, consider if 3 are "Display" and 7 are "Secondary" (relegated to a `body-sm` list).



---



## 7. Scaling & Spacing

Consistency is the bedrock of trust. Use the following increments religiously:

* **Layout Margin:** `spacing-16` (3.5rem) for desktop gutters.

* **Component Internal Padding:** `spacing-4` (0.9rem).

* **Section Gaps:** `spacing-10` (2.25rem).



By adhering to this system, we ensure that the interface feels less like a tool and more like a high-end financial advisor: calm, organized, and impeccably presented.