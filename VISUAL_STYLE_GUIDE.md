# 🎨 Visual Style Guide - Modern LCOJ Theme

## Color Palette

### Primary Colors (Sky Blue)
```css
--primary-50:  #f0f9ff  ███████  Very Light - Hover backgrounds
--primary-100: #e0f2fe  ███████  Light - Subtle highlights
--primary-500: #0ea5e9  ███████  Main - Primary actions ⭐
--primary-600: #0284c7  ███████  Dark - Hover states
--primary-700: #0369a1  ███████  Darker - Active states
```

### Neutral Colors (Grays)
```css
--gray-50:  #f9fafb  ███████  Backgrounds
--gray-100: #f3f4f6  ███████  Cards, table headers
--gray-200: #e5e7eb  ███████  Borders
--gray-300: #d1d5db  ███████  Input borders
--gray-500: #6b7280  ███████  Secondary text
--gray-700: #374151  ███████  Primary text
--gray-900: #111827  ███████  Headings
```

### Status Colors
```css
--success-500: #22c55e  ███████  Green - Success states
--warning-500: #f59e0b  ███████  Amber - Warnings
--error-500:   #ef4444  ███████  Red - Errors
```

---

## Component Examples

### Buttons

#### Primary Button
```html
<button class="button">Submit Solution</button>
```
**Style:**
- Background: #0ea5e9 (Sky Blue)
- Text: White
- Padding: 0.5rem 1rem
- Border Radius: 0.375rem (6px)
- Shadow: Small, grows on hover
- Animation: Lifts up 1px on hover

**States:**
- Default: Blue with subtle shadow
- Hover: Darker blue (#0284c7) + lift effect
- Active: Darkest blue (#0369a1) + pressed
- Disabled: Gray with 60% opacity

#### Secondary Button
```html
<button class="button button-secondary">Cancel</button>
```
**Style:**
- Background: #f3f4f6 (Light Gray)
- Text: #374151 (Dark Gray)
- Same padding and radius
- Lighter visual weight

---

### Form Inputs

#### Text Input
```html
<input type="text" placeholder="Search problems...">
```
**Style:**
- Border: 1px solid #d1d5db
- Padding: 0.5rem 0.75rem
- Border Radius: 0.375rem
- Background: White
- Placeholder: #6b7280 (Gray)

**Focus State:**
- Border: #0ea5e9 (Blue)
- Ring: 3px rgba(14, 165, 233, 0.1)
- No outline

#### Checkbox
```html
<input type="checkbox" checked>
```
**Style:**
- Size: 1rem × 1rem
- Border: 1.5px solid #6b7280
- Border Radius: 0.25rem
- Checked: Blue (#0ea5e9) with white checkmark SVG
- Smooth transition

---

### Tables

#### Structure
```
┌─────────────────────────────────────────────┐
│ Table with rounded corners and shadow       │
├─────────────────────────────────────────────┤
│ #   │ Problem Name    │ Points │ Solved    │ ← Light gray header
├─────┼─────────────────┼────────┼───────────┤
│ 001 │ Hello World     │ 100    │ 1,234     │ ← White row
├─────┼─────────────────┼────────┼───────────┤
│ 002 │ Binary Search   │ 150    │ 856       │ ← Hover: Light gray
└─────┴─────────────────┴────────┴───────────┘
```

**Header:**
- Background: #f9fafb (Light gray, not dark!)
- Text: #374151 (Dark gray, not white!)
- Font: 0.875rem, UPPERCASE, semibold
- Letter spacing: 0.05em

**Body:**
- Background: White
- Border: #e5e7eb (very light)
- Hover: #f9fafb background
- Padding: 0.75rem 1rem

---

### Cards & Sideboxes

#### Card Structure
```
┌────────────────────────────────┐
│ ┌─────────────────────────────┐│
│ │ CARD TITLE          ⓘ      ││ ← Light gray header
│ └─────────────────────────────┘│
│                                │
│  Card content here...          │ ← White body
│  More content...               │
│                                │
└────────────────────────────────┘
  ↑ Subtle shadow
```

**Style:**
- Container: White background, rounded
- Border: 1px solid #e5e7eb
- Border Radius: 0.5rem (8px)
- Shadow: 0 1px 3px rgba(0, 0, 0, 0.1)

**Header:**
- Background: #f9fafb
- Text: #374151, UPPERCASE, 1rem, semibold
- Border Bottom: 1px solid #e5e7eb
- Padding: 1rem 1.25rem

**Body:**
- Padding: 1rem 1.25rem
- No background (inherits white)

---

### Navigation Bar

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Logo  HOME  PROBLEMS  CONTESTS  USERS     🔔 VI EN [User]  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
  ↑ White background with subtle shadow
```

**Style:**
- Background: White (#ffffff)
- Border Bottom: 1px solid #e5e7eb
- Shadow: 0 2px 4px rgba(0, 0, 0, 0.1)
- Height: 56px

**Menu Items:**
- Text: #374151 (Gray, not white!)
- Font: Source Sans Pro, 500 weight
- Padding: 14px 10px
- Border Radius: 0.375rem

**States:**
- Default: Gray text
- Hover: Blue text (#0ea5e9) on light blue bg (#f0f9ff)
- Active: White text on blue bg (#0ea5e9)

**Dropdown:**
- Background: White
- Border: 1px solid #e5e7eb
- Shadow: Medium (0 4px 6px)
- Border Radius: 0.5rem
- Hover: Light gray background

---

### Problem List

#### Filter Form
```
┌─────────────────────────────────────────────┐
│ Filter Problems                             │
│                                             │
│ Search: [________________]  🔍 Search       │
│                                             │
│ Category: [All Categories ▼]                │
│                                             │
│ Type: [All Types ▼]                        │
└─────────────────────────────────────────────┘
```

**Style:**
- White card with shadow
- Rounded corners
- Labels: Semibold
- Inputs: Full width
- Buttons: Modern style

#### Problem Row
```
Problem Code │ Problem Name → Hover: light blue │ Points │ AC
─────────────┼───────────────────────────────────┼────────┼────
001          │ Hello World                       │ 100    │ 90%
             │ ☰ easy  ☰ implementation         │        │
```

**Hover Effect:**
- Background: #f9fafb
- Slight scale transform
- Smooth transition

---

### Contest List

#### Contest Row with Tags
```
┌─────────────────────────────────────────────────────────┐
│ Contest Name                                            │
│ ⚫ hidden  🔒 private  📊 rated                         │
│                                                         │
│ Start: Dec 1, 2025 10:00  │  Duration: 2 hours        │
└─────────────────────────────────────────────────────────┘
```

**Tag Style:**
- Shape: Pill (fully rounded)
- Padding: 0.375rem 0.75rem
- Font: 0.75rem
- Icon + text
- Hover: Lift effect

**Tag Colors:**
- Hidden: Black bg, white text
- Private: Gray bg, dark text
- Rated: Red/orange bg, white text
- Organization: Light gray bg

---

### Blog Posts

#### Post Card
```
┌────────────────────────────────────────────┐
│                                            │
│  Post Title Here                           │ ← Bold, 1.5rem
│  ───────────────────────────────────────   │
│                                            │
│  │ Post excerpt or content...              │ ← Blue left border
│  │ More text here...                       │
│                                            │
│  ───────────────────────────────────────   │
│  👤 Author  •  📅 Date  •  💬 Comments    │ ← Meta bar
│                                            │
└────────────────────────────────────────────┘
  ↑ Hover: Lifts up with larger shadow
```

**Style:**
- Card: White with border and shadow
- Border Radius: 0.5rem
- Padding: 1.5rem
- Hover: translateY(-2px) + shadow increase

**Meta Bar:**
- Background: #f9fafb
- Border: Top and bottom
- Flex layout with gap
- Font size: 0.875rem
- Color: #6b7280

---

## Shadow System

### Small Shadow (Cards, inputs)
```css
box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1),
            0 1px 2px -1px rgba(0, 0, 0, 0.1);
```

### Medium Shadow (Dropdowns, hovers)
```css
box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
            0 2px 4px -2px rgba(0, 0, 0, 0.1);
```

### Large Shadow (Modals, important cards)
```css
box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1),
            0 4px 6px -4px rgba(0, 0, 0, 0.1);
```

---

## Border Radius Scale

```css
--radius-sm:   0.25rem  (4px)   ▢  Small elements
--radius-md:   0.375rem (6px)   ▢  Buttons, inputs
--radius-lg:   0.5rem   (8px)   ▢  Cards, containers
--radius-xl:   0.75rem  (12px)  ▢  Large panels
--radius-full: 9999px           ●  Pills, badges
```

---

## Spacing Scale

```css
--spacing-xs:  0.25rem  (4px)   Tight spacing
--spacing-sm:  0.5rem   (8px)   Small gaps
--spacing-md:  1rem     (16px)  Default spacing
--spacing-lg:  1.5rem   (24px)  Section spacing
--spacing-xl:  2rem     (32px)  Large gaps
--spacing-2xl: 3rem     (48px)  Major sections
```

---

## Typography Scale

### Font Families
```css
Primary: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto
Code:    Consolas, Monaco, "Courier New", monospace
```

### Sizes
```css
h2: 1.875rem (30px) - Page titles
h3: 1.5rem   (24px) - Section titles
h4: 1.25rem  (20px) - Subsections
p:  1rem     (16px) - Body text
small: 0.875rem (14px) - Meta info
tiny: 0.75rem (12px) - Labels
```

### Weights
```css
Regular:  400
Medium:   500  (UI elements)
Semibold: 600  (Headings, emphasis)
Bold:     700  (Strong emphasis)
```

---

## Animation Timings

### Standard Transition
```css
transition: all 0.2s ease;
```

### Hover Effects
```css
transform: translateY(-1px);  /* Lift */
transform: scale(1.001);       /* Subtle grow */
```

### Focus Ring
```css
box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1);
```

---

## Accessibility Features

### Focus States
✅ All interactive elements have visible focus
✅ Focus ring: 3px blue with transparency
✅ No outline removal without alternative

### Contrast Ratios
✅ Text on backgrounds: Minimum 4.5:1
✅ Large text: Minimum 3:1
✅ UI components: Minimum 3:1

### Color Blindness
✅ Not relying solely on color
✅ Icons + text combinations
✅ Multiple indicators for status

---

## Common Patterns

### Hover State Pattern
```css
.element {
  transition: all 0.2s ease;
}

.element:hover {
  background: lighter-color;
  box-shadow: larger-shadow;
  transform: translateY(-1px);
}
```

### Focus State Pattern
```css
.input:focus {
  border-color: #0ea5e9;
  box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1);
  outline: none;
}
```

### Card Pattern
```css
.card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}
```

---

## Quick Reference

### Most Used Colors
- **Primary Action**: `#0ea5e9`
- **Text**: `#374151`
- **Background**: `#f9fafb`
- **Border**: `#e5e7eb`
- **Hover**: `#f0f9ff`

### Most Used Spacing
- **Card padding**: `1rem - 1.5rem`
- **Button padding**: `0.5rem 1rem`
- **Input padding**: `0.5rem 0.75rem`
- **Section margin**: `1rem - 2rem`

### Most Used Radius
- **Buttons/Inputs**: `0.375rem`
- **Cards**: `0.5rem`
- **Pills**: `9999px`

---

**Last Updated:** November 30, 2025
**Version:** 1.0
**Theme:** Modern Flat Design
